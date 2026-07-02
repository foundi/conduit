import base64
import hashlib
import re
import time
from typing import Any, Dict, List, Optional, Union

from conduit.client.base import BasePhabricatorClient, PhabricatorAPIError
from conduit.utils import build_search_params
from conduit.utils.remarkup import resolve_file_identifiers


class FileClient(BasePhabricatorClient):
    # Threshold above which `upload_bytes` switches to chunked upload.
    CHUNK_THRESHOLD_BYTES = 4 * 1024 * 1024
    CHUNK_SIZE_BYTES = 4 * 1024 * 1024
    # Polling budget for `wait_for_chunks_complete` (30 * 1.0 = 30 s total).
    CHUNK_POLL_MAX_ATTEMPTS = 30
    CHUNK_POLL_INTERVAL_SECONDS = 1.0

    def search_files(
        self,
        constraints: Dict[str, Any] = None,
        order: Optional[Union[str, List[str]]] = None,
        before: Optional[str] = None,
        after: Optional[str] = None,
        limit: int = 100,
    ) -> Dict[str, Any]:
        """
        Read information about files.

        Args:
            constraints: Search constraints
            order: Result ordering (builtin key or custom column list)
            before: Cursor for previous page
            after: Cursor for next page
            limit: Maximum number of results to return

        Returns:
            Search results with file data
        """
        params = build_search_params(
            constraints=constraints,
            order=order,
            before=before,
            after=after,
            limit=limit,
        )
        return self._make_request("file.search", params)

    def get_file_info(self, file_phid: str) -> Dict[str, Any]:
        """
        Get information about a file.

        Args:
            file_phid: PHID of the file

        Returns:
            File information
        """
        # Delegate to search_files so constraints are flattened consistently
        # via build_search_params (Phorge rejects nested-dict form bodies).
        result = self.search_files(
            constraints={"phids": [file_phid]}, limit=1
        )

        if result.get("data"):
            return result["data"][0]
        else:
            raise PhabricatorAPIError(f"File {file_phid} not found")

    def allocate_file(
        self, name: str, length: int, content_hash: str = None
    ) -> Dict[str, Any]:
        """
        Prepare to upload a file.

        Args:
            name: File name
            length: File length in bytes
            content_hash: Optional content hash for dedupe

        Returns:
            Allocation information including ``filePHID`` and an
            ``upload`` boolean indicating whether chunked upload is
            required (``False`` means Phorge already had the hash).
        """
        params = {"name": name, "contentLength": length}
        if content_hash:
            params["contentHash"] = content_hash

        return self._make_request("file.allocate", params)

    def upload_file(self, data: bytes, name: str = None) -> Dict[str, Any]:
        """
        Upload a file to the server.

        Args:
            data: Raw file bytes; base64-encoded before transport.
            name: Optional file name

        Returns:
            Upload result
        """
        encoded = base64.b64encode(data).decode("ascii")
        params = {"data_base64": encoded}
        if name:
            params["name"] = name

        return self._make_request("file.upload", params)

    def upload_chunk(
        self, file_phid: str, byte_start: int, data: bytes
    ) -> Dict[str, Any]:
        """
        Upload a chunk of file data to the server.

        Args:
            file_phid: File PHID
            byte_start: Starting byte position
            data: Raw chunk bytes; base64-encoded before transport.

        Returns:
            Upload result
        """
        encoded = base64.b64encode(data).decode("ascii")
        return self._make_request(
            "file.uploadchunk",
            {
                "filePHID": file_phid,
                "byteStart": byte_start,
                "data": encoded,
                "dataEncoding": "base64",
            },
        )

    def query_chunks(self, file_phid: str) -> Dict[str, Any]:
        """
        Get information about file chunks.

        Args:
            file_phid: File PHID

        Returns:
            Chunk information
        """
        return self._make_request("file.querychunks", {"filePHID": file_phid})

    def download_file(self, file_phid: str) -> Dict[str, Any]:
        """
        Download a file from the server.

        Args:
            file_phid: File PHID

        Returns:
            File data
        """
        return self._make_request("file.download", {"phid": file_phid})

    def upload_bytes(
        self,
        data: bytes,
        name: str,
        mime_type: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Upload raw bytes via inline or chunked routing.

        Files below :attr:`CHUNK_THRESHOLD_BYTES` are uploaded inline by
        passing ``dataBase64`` directly to ``file.allocate``. Larger files
        go through ``file.allocate`` (without inline data) and then a
        sequence of ``file.uploadchunk`` calls, finalised by
        :meth:`wait_for_chunks_complete`.

        ``mime_type`` is accepted for forward-compatibility but Phorge
        primarily infers the type from ``name``.

        Returns a dict with keys ``phid``, ``id``, ``monogram``, ``url``,
        ``size_bytes`` and ``deduped`` (``True`` when Phorge recognised
        the SHA-256 hash and skipped the chunked upload entirely).
        """
        del mime_type  # accepted for API symmetry; Phorge infers from name
        size = len(data)
        content_hash = hashlib.sha256(data).hexdigest()

        # Always call file.allocate first — Phorge's response tells us
        # what to do next instead of us guessing from file size:
        #   {upload: false, filePHID: "..."}  → dedupe; file already on server
        #   {upload: true,  filePHID: "..."}  → chunked upload to this PHID
        #   {upload: true,  filePHID: null}   → too small for chunks; use file.upload
        # The chunk threshold is configured per-Phorge-instance, so letting
        # the server decide is more robust than hard-coding our own.
        alloc = self.allocate_file(
            name=name, length=size, content_hash=content_hash
        )
        file_phid = alloc.get("filePHID")
        needs_upload = bool(alloc.get("upload"))

        if file_phid and not needs_upload:
            deduped = True
        elif file_phid and needs_upload:
            for offset in range(0, size, self.CHUNK_SIZE_BYTES):
                chunk = data[offset:offset + self.CHUNK_SIZE_BYTES]
                self.upload_chunk(file_phid, offset, chunk)
            self.wait_for_chunks_complete(file_phid)
            deduped = False
        else:
            # filePHID is None — Phorge wants the legacy single-shot path.
            upload_result = self.upload_file(data, name=name)
            if isinstance(upload_result, str):
                file_phid = upload_result
            elif isinstance(upload_result, dict):
                file_phid = upload_result.get("filePHID")
            deduped = False

        if not file_phid:
            raise PhabricatorAPIError(
                f"file upload returned no filePHID for {name!r}"
            )

        info = self.get_file_info(file_phid)
        file_id = int(info["id"])
        return {
            "phid": info["phid"],
            "id": file_id,
            "monogram": f"F{file_id}",
            "url": self._build_file_url(file_id),
            "size_bytes": int(
                info.get("fields", {}).get("size", size)
            ),
            "deduped": deduped,
        }

    def resolve_file_id(self, identifier: str) -> int:
        """Resolve ``"F<n>"`` or ``"PHID-FILE-..."`` to a numeric file id."""
        return resolve_file_identifiers(
            [identifier], self.get_file_info
        )[0]

    def wait_for_chunks_complete(
        self,
        file_phid: str,
        max_attempts: Optional[int] = None,
        interval_seconds: Optional[float] = None,
    ) -> None:
        """Poll ``file.querychunks`` until upload is complete.

        Raises :class:`PhabricatorAPIError` once the polling budget is
        exhausted so a stalled upload fails loudly instead of silently
        producing a partial file.
        """
        attempts = (
            max_attempts
            if max_attempts is not None
            else self.CHUNK_POLL_MAX_ATTEMPTS
        )
        interval = (
            interval_seconds
            if interval_seconds is not None
            else self.CHUNK_POLL_INTERVAL_SECONDS
        )
        for _ in range(attempts):
            result = self.query_chunks(file_phid)
            if self._chunks_complete(result):
                return
            time.sleep(interval)
        raise PhabricatorAPIError(
            f"chunk upload for {file_phid} did not complete within "
            f"{attempts * interval:.0f} seconds"
        )

    @staticmethod
    def _chunks_complete(query_result: Dict[str, Any]) -> bool:
        # Phorge versions differ: some surface a top-level "complete"
        # boolean, others only return a per-chunk list.
        if "complete" in query_result:
            return bool(query_result["complete"])
        chunks = query_result.get("chunks", [])
        return bool(chunks) and all(
            c.get("complete", False) for c in chunks
        )

    def _build_file_url(self, file_id: int) -> str:
        base = re.sub(r"/api/?$", "", self.api_url)
        return f"{base}/F{file_id}"

    def get_file_info_legacy(
        self, file_id: int = None, file_phid: str = None
    ) -> Dict[str, Any]:
        """
        Get information about a file (legacy method).

        Args:
            file_id: File ID
            file_phid: File PHID

        Returns:
            File information
        """
        params = {}
        if file_id:
            params["id"] = file_id
        if file_phid:
            params["phid"] = file_phid

        return self._make_request("file.info", params)
