"""Tests for file client."""

import base64

import pytest
from unittest.mock import patch

from conduit.client.file import FileClient
from conduit.client.base import PhabricatorAPIError


class TestFileClient:
    """Test FileClient methods."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = FileClient(
            api_url="http://test.example.com/api/", api_token="test_token"
        )

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_search_files_success(self, mock_request):
        """Test successful file search."""
        mock_request.return_value = {
            "data": [
                {"phid": "PHID-FILE-1", "name": "test.txt"},
                {"phid": "PHID-FILE-2", "name": "example.pdf"},
            ]
        }

        result = self.client.search_files(constraints={"name": "test"}, limit=10)

        mock_request.assert_called_once_with(
            "file.search",
            {
                "constraints[name]": "test",
                "limit": 10,
            },
        )
        assert result["data"][0]["name"] == "test.txt"

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_search_files_no_constraints(self, mock_request):
        """Test file search without constraints."""
        mock_request.return_value = {"data": []}

        result = self.client.search_files()

        mock_request.assert_called_once_with(
            "file.search",
            {
                "limit": 100,
            },
        )
        assert result["data"] == []

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_get_file_info_success(self, mock_request):
        """Test successful file info retrieval."""
        mock_request.return_value = {
            "data": [
                {
                    "phid": "PHID-FILE-1",
                    "name": "test.txt",
                    "size": 1024,
                    "mimeType": "text/plain",
                }
            ]
        }

        result = self.client.get_file_info("PHID-FILE-1")

        mock_request.assert_called_once_with(
            "file.search",
            {
                "constraints[phids][0]": "PHID-FILE-1",
                "limit": 1,
            },
        )
        assert result["name"] == "test.txt"
        assert result["size"] == 1024

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_get_file_info_not_found(self, mock_request):
        """Test file info retrieval when file not found."""
        mock_request.return_value = {"data": []}

        with pytest.raises(PhabricatorAPIError) as exc_info:
            self.client.get_file_info("PHID-NONEXISTENT")

        assert "PHID-NONEXISTENT not found" in str(exc_info.value)

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_allocate_file_success(self, mock_request):
        """Test successful file allocation."""
        mock_request.return_value = {
            "filePHID": "PHID-FILE-1",
            "uploadURI": "http://example.com/upload",
        }

        result = self.client.allocate_file(
            name="test.txt", length=1024, content_hash="abc123"
        )

        mock_request.assert_called_once_with(
            "file.allocate",
            {
                "name": "test.txt",
                "contentLength": 1024,
                "contentHash": "abc123",
            },
        )
        assert result["filePHID"] == "PHID-FILE-1"

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_allocate_file_without_hash(self, mock_request):
        """Test file allocation without content hash."""
        mock_request.return_value = {
            "filePHID": "PHID-FILE-1",
        }

        result = self.client.allocate_file(name="test.txt", length=1024)

        mock_request.assert_called_once_with(
            "file.allocate",
            {
                "name": "test.txt",
                "contentLength": 1024,
            },
        )
        assert result["filePHID"] == "PHID-FILE-1"

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_upload_file_success(self, mock_request):
        """Test successful file upload."""
        mock_request.return_value = {
            "filePHID": "PHID-FILE-1",
            "uri": "http://example.com/file/1",
        }

        data = b"file content"
        result = self.client.upload_file(data, name="test.txt")

        mock_request.assert_called_once_with(
            "file.upload",
            {
                "data_base64": base64.b64encode(data).decode("ascii"),
                "name": "test.txt",
            },
        )
        assert result["filePHID"] == "PHID-FILE-1"

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_upload_file_without_name(self, mock_request):
        """Test file upload without name."""
        mock_request.return_value = {
            "filePHID": "PHID-FILE-1",
        }

        data = b"file content"
        result = self.client.upload_file(data)

        mock_request.assert_called_once_with(
            "file.upload",
            {
                "data_base64": base64.b64encode(data).decode("ascii"),
            },
        )
        assert result["filePHID"] == "PHID-FILE-1"

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_upload_chunk_success(self, mock_request):
        """Test successful chunk upload."""
        mock_request.return_value = {
            "complete": False,
            "uploaded": 1024,
        }

        data = b"chunk content"
        result = self.client.upload_chunk(
            file_phid="PHID-FILE-1", byte_start=0, data=data
        )

        mock_request.assert_called_once_with(
            "file.uploadchunk",
            {
                "filePHID": "PHID-FILE-1",
                "byteStart": 0,
                "data": base64.b64encode(data).decode("ascii"),
                "dataEncoding": "base64",
            },
        )
        assert result["uploaded"] == 1024

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_query_chunks_success(self, mock_request):
        """Test successful chunk query."""
        mock_request.return_value = {
            "complete": True,
            "chunks": [
                {"byteStart": 0, "byteEnd": 1024},
                {"byteStart": 1024, "byteEnd": 2048},
            ],
        }

        result = self.client.query_chunks("PHID-FILE-1")

        mock_request.assert_called_once_with(
            "file.querychunks",
            {
                "filePHID": "PHID-FILE-1",
            },
        )
        assert len(result["chunks"]) == 2

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_download_file_success(self, mock_request):
        """Test successful file download."""
        mock_request.return_value = {
            "data_base64": "ZmlsZSBjb250ZW50",  # base64 encoded "file content"
            "name": "test.txt",
        }

        result = self.client.download_file("PHID-FILE-1")

        mock_request.assert_called_once_with(
            "file.download",
            {
                "phid": "PHID-FILE-1",
            },
        )
        assert result["name"] == "test.txt"

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_get_file_info_legacy_with_id(self, mock_request):
        """Test legacy file info retrieval with ID."""
        mock_request.return_value = {
            "id": 123,
            "phid": "PHID-FILE-123",
            "name": "test.txt",
        }

        result = self.client.get_file_info_legacy(file_id=123)

        mock_request.assert_called_once_with(
            "file.info",
            {
                "id": 123,
            },
        )
        assert result["id"] == 123

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_get_file_info_legacy_with_phid(self, mock_request):
        """Test legacy file info retrieval with PHID."""
        mock_request.return_value = {
            "id": 123,
            "phid": "PHID-FILE-123",
            "name": "test.txt",
        }

        result = self.client.get_file_info_legacy(file_phid="PHID-FILE-123")

        mock_request.assert_called_once_with(
            "file.info",
            {
                "phid": "PHID-FILE-123",
            },
        )
        assert result["phid"] == "PHID-FILE-123"

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_get_file_info_legacy_no_parameters(self, mock_request):
        """Test legacy file info retrieval with no parameters."""
        mock_request.return_value = {
            "id": 123,
            "phid": "PHID-FILE-123",
            "name": "test.txt",
        }

        result = self.client.get_file_info_legacy()

        mock_request.assert_called_once_with("file.info", {})
        assert result["id"] == 123

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_upload_bytes_small_falls_back_to_file_upload(self, mock_request):
        """When file.allocate returns null filePHID, fall back to file.upload."""
        data = b"hello world"
        mock_request.side_effect = [
            # file.allocate signals "too small for chunks, use file.upload".
            {"upload": True, "filePHID": None},
            # file.upload returns the bare file PHID string.
            "PHID-FILE-1",
            {
                "data": [
                    {
                        "id": 42,
                        "phid": "PHID-FILE-1",
                        "fields": {"size": len(data), "name": "x.txt"},
                    }
                ]
            },
        ]

        result = self.client.upload_bytes(data, name="x.txt")

        methods = [call.args[0] for call in mock_request.call_args_list]
        assert methods == ["file.allocate", "file.upload", "file.search"]

        upload_params = mock_request.call_args_list[1].args[1]
        assert upload_params["name"] == "x.txt"
        assert upload_params["data_base64"] == base64.b64encode(data).decode(
            "ascii"
        )

        assert result["phid"] == "PHID-FILE-1"
        assert result["id"] == 42
        assert result["monogram"] == "F42"
        assert result["size_bytes"] == len(data)
        assert result["deduped"] is False
        assert result["url"].endswith("/F42")

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_upload_bytes_dedupe_path(self, mock_request):
        """Phorge dedupe: allocate returns upload=False with a filePHID."""
        data = b"some content"
        mock_request.side_effect = [
            {"filePHID": "PHID-FILE-9", "upload": False},
            {
                "data": [
                    {
                        "id": 7,
                        "phid": "PHID-FILE-9",
                        "fields": {"size": len(data), "name": "big.bin"},
                    }
                ]
            },
        ]

        result = self.client.upload_bytes(data, name="big.bin")

        methods = [call.args[0] for call in mock_request.call_args_list]
        assert methods == ["file.allocate", "file.search"]
        assert result["deduped"] is True
        assert result["id"] == 7

    @patch("conduit.client.file.time.sleep")
    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_upload_bytes_chunked_path(self, mock_request, mock_sleep):
        """Large new file uploads via chunks and polls until complete."""
        # 2 chunks of CHUNK_SIZE_BYTES each.
        chunk_size = FileClient.CHUNK_SIZE_BYTES
        data = b"\x01" * (chunk_size * 2)
        mock_request.side_effect = [
            {"filePHID": "PHID-FILE-2", "upload": True},  # allocate
            {"complete": False},                          # chunk 1
            {"complete": False},                          # chunk 2
            {"complete": True},                           # querychunks
            {
                "data": [
                    {
                        "id": 99,
                        "phid": "PHID-FILE-2",
                        "fields": {"size": len(data), "name": "big.bin"},
                    }
                ]
            },
        ]

        result = self.client.upload_bytes(data, name="big.bin")

        methods = [call.args[0] for call in mock_request.call_args_list]
        assert methods == [
            "file.allocate",
            "file.uploadchunk",
            "file.uploadchunk",
            "file.querychunks",
            "file.search",
        ]
        assert result["id"] == 99
        assert result["deduped"] is False

    @patch("conduit.client.file.time.sleep")
    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_wait_for_chunks_complete_times_out(
        self, mock_request, mock_sleep
    ):
        """Bounded poll loop raises when budget exhausts."""
        mock_request.return_value = {"complete": False}

        with pytest.raises(PhabricatorAPIError, match="did not complete"):
            self.client.wait_for_chunks_complete(
                "PHID-FILE-1", max_attempts=3, interval_seconds=0.01
            )

        assert mock_request.call_count == 3

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_resolve_file_id_monogram_fast_path(self, mock_request):
        """Monogram parses inline without any API call."""
        result = self.client.resolve_file_id("F1234")
        assert result == 1234
        assert mock_request.call_count == 0

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_resolve_file_id_phid_uses_file_search(self, mock_request):
        """PHID input hits file.search and returns numeric id."""
        mock_request.return_value = {
            "data": [{"id": 42, "phid": "PHID-FILE-abc"}]
        }

        result = self.client.resolve_file_id("PHID-FILE-abc")

        assert result == 42
        mock_request.assert_called_once_with(
            "file.search",
            {
                "constraints[phids][0]": "PHID-FILE-abc",
                "limit": 1,
            },
        )

    def test_resolve_file_id_invalid_raises(self):
        with pytest.raises(ValueError, match="invalid file identifier"):
            self.client.resolve_file_id("not-a-file-id")

    def test_chunks_complete_top_level_flag(self):
        assert FileClient._chunks_complete({"complete": True}) is True
        assert FileClient._chunks_complete({"complete": False}) is False

    def test_chunks_complete_per_chunk_aggregation(self):
        assert FileClient._chunks_complete(
            {"chunks": [{"complete": True}, {"complete": True}]}
        ) is True
        assert FileClient._chunks_complete(
            {"chunks": [{"complete": True}, {"complete": False}]}
        ) is False
        # Empty/missing chunks is treated as incomplete to avoid races.
        assert FileClient._chunks_complete({"chunks": []}) is False
        assert FileClient._chunks_complete({}) is False

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_get_file_info_legacy_both_parameters(self, mock_request):
        """Test legacy file info retrieval with both ID and PHID."""
        mock_request.return_value = {
            "id": 123,
            "phid": "PHID-FILE-123",
            "name": "test.txt",
        }

        result = self.client.get_file_info_legacy(
            file_id=123, file_phid="PHID-FILE-123"
        )

        mock_request.assert_called_once_with(
            "file.info",
            {
                "id": 123,
                "phid": "PHID-FILE-123",
            },
        )
        assert result["id"] == 123


class TestFileClientSearchPagination:
    """Test cursor pagination params on FileClient.search_files."""

    def setup_method(self):
        """Set up test fixtures."""
        self.client = FileClient(
            api_url="http://test.example.com/api/", api_token="test_token"
        )

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_search_files_forwards_pagination_params(self, mock_request):
        """Pagination params are serialized into the request payload."""
        mock_request.return_value = {"data": []}

        self.client.search_files(
            order="newest", before="10", after="42", limit=50
        )

        mock_request.assert_called_once_with(
            "file.search",
            {
                "limit": 50,
                "order": "newest",
                "before": "10",
                "after": "42",
            },
        )

    @patch("conduit.client.base.BasePhabricatorClient._make_request")
    def test_search_files_omits_pagination_by_default(self, mock_request):
        """Pagination params are absent from the payload when unset."""
        mock_request.return_value = {"data": []}

        self.client.search_files()

        mock_request.assert_called_once_with(
            "file.search", {"limit": 100}
        )
