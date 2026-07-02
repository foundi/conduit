"""Mock-based tests for the file-related MCP tools.

These tests register tools against a lightweight :class:`CapturingMCP` and
exercise the resulting functions directly, mocking the underlying
``PhabricatorClient`` rather than the FastMCP server itself.
"""

import base64
from unittest.mock import MagicMock

import pytest

from conduit.main_tools import (
    _fetch_file_legacy_info,
    _inject_file_refs,
    _read_upload_bytes,
    register_tools,
)


class CapturingMCP:
    """Stand-in for ``FastMCP`` that records registered tool functions."""

    def __init__(self):
        self.tools = {}

    def tool(self, *args, **kwargs):
        def decorator(func):
            self.tools[func.__name__] = func
            return func

        return decorator


@pytest.fixture
def tools():
    mcp = CapturingMCP()
    client = MagicMock()
    register_tools(mcp, lambda: client)
    return mcp.tools, client


class TestReadUploadBytes:
    def test_base64_decoded(self):
        encoded = base64.b64encode(b"hello").decode("ascii")
        assert _read_upload_bytes(encoded, None) == b"hello"

    def test_path_read(self, tmp_path):
        target = tmp_path / "x.bin"
        target.write_bytes(b"\x00\x01\x02")
        assert _read_upload_bytes(None, str(target)) == b"\x00\x01\x02"

    def test_neither_raises(self):
        with pytest.raises(ValueError, match="exactly one"):
            _read_upload_bytes(None, None)

    def test_both_raises(self):
        with pytest.raises(ValueError, match="exactly one"):
            _read_upload_bytes("Zm9v", "/tmp/x")


class TestFetchFileLegacyInfo:
    def test_monogram_uses_id(self):
        client = MagicMock()
        client.file.get_file_info_legacy.return_value = {"id": 7}

        result = _fetch_file_legacy_info(client, "F7")

        client.file.get_file_info_legacy.assert_called_once_with(file_id=7)
        assert result == {"id": 7}

    def test_phid_uses_phid(self):
        client = MagicMock()
        client.file.get_file_info_legacy.return_value = {"phid": "PHID-FILE-x"}

        _fetch_file_legacy_info(client, "PHID-FILE-x")

        client.file.get_file_info_legacy.assert_called_once_with(
            file_phid="PHID-FILE-x"
        )

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="invalid file identifier"):
            _fetch_file_legacy_info(MagicMock(), "garbage")


class TestInjectFileRefs:
    def test_no_phids_returns_text_unchanged(self):
        assert _inject_file_refs("hello", None, MagicMock()) == "hello"
        assert _inject_file_refs("hello", [], MagicMock()) == "hello"

    def test_monogram_appended_without_api_call(self):
        client = MagicMock()
        result = _inject_file_refs("hello", ["F42"], client)
        assert result == "hello\n\n{F42}"
        client.file.get_file_info.assert_not_called()

    def test_phid_resolved_via_client(self):
        client = MagicMock()
        client.file.get_file_info.return_value = {"id": 99}
        result = _inject_file_refs("hello", ["PHID-FILE-x"], client)
        assert result == "hello\n\n{F99}"

    def test_idempotent_when_already_present(self):
        client = MagicMock()
        result = _inject_file_refs("see {F42}", ["F42"], client)
        assert result == "see {F42}"


class TestPhaFileUpload:
    def test_xor_validation_neither(self, tools):
        functions, _ = tools
        result = functions["pha_file_upload"](filename="x.png")
        assert result["success"] is False
        assert "exactly one" in result["error"]

    def test_xor_validation_both(self, tools):
        functions, _ = tools
        result = functions["pha_file_upload"](
            filename="x.png", content_base64="Zm9v", source_path="/tmp/x"
        )
        assert result["success"] is False
        assert "exactly one" in result["error"]

    def test_small_inline_upload(self, tools):
        functions, client = tools
        client.file.upload_bytes.return_value = {
            "phid": "PHID-FILE-1",
            "id": 42,
            "monogram": "F42",
            "url": "https://example.com/F42",
            "size_bytes": 5,
            "deduped": False,
        }

        result = functions["pha_file_upload"](
            filename="x.txt",
            content_base64=base64.b64encode(b"hello").decode("ascii"),
        )

        assert result["success"] is True
        assert result["file"]["remarkup_ref"] == "{F42}"
        assert result["file"]["monogram"] == "F42"
        client.file.upload_bytes.assert_called_once()
        kwargs = client.file.upload_bytes.call_args.kwargs
        assert kwargs["data"] == b"hello"
        assert kwargs["name"] == "x.txt"

    def test_source_path_upload(self, tools, tmp_path):
        functions, client = tools
        target = tmp_path / "data.bin"
        target.write_bytes(b"\xff\xfe")
        client.file.upload_bytes.return_value = {
            "phid": "PHID-FILE-9",
            "id": 9,
            "monogram": "F9",
            "url": "https://example.com/F9",
            "size_bytes": 2,
            "deduped": False,
        }

        result = functions["pha_file_upload"](
            filename="data.bin", source_path=str(target)
        )

        assert result["success"] is True
        assert client.file.upload_bytes.call_args.kwargs["data"] == b"\xff\xfe"


class TestPhaFileDownload:
    def test_download_by_monogram(self, tools):
        functions, client = tools
        client.file.get_file_info_legacy.return_value = {
            "id": 42,
            "phid": "PHID-FILE-1",
            "name": "report.pdf",
            "mimeType": "application/pdf",
            "byteSize": "1024",
        }
        client.file.download_file.return_value = "ZmlsZQ=="

        result = functions["pha_file_download"](file="F42")

        assert result["success"] is True
        assert result["file"]["id"] == 42
        assert result["file"]["monogram"] == "F42"
        assert result["file"]["content_base64"] == "ZmlsZQ=="
        assert result["file"]["mime_type"] == "application/pdf"
        assert result["file"]["size_bytes"] == 1024
        client.file.get_file_info_legacy.assert_called_once_with(file_id=42)
        client.file.download_file.assert_called_once_with(
            file_phid="PHID-FILE-1"
        )

    def test_download_by_phid(self, tools):
        functions, client = tools
        client.file.get_file_info_legacy.return_value = {
            "id": 99,
            "phid": "PHID-FILE-abc",
            "name": "img.png",
            "mimeType": "image/png",
            "byteSize": 8421,
        }
        client.file.download_file.return_value = {"data_base64": "AAAA"}

        result = functions["pha_file_download"](file="PHID-FILE-abc")

        assert result["success"] is True
        assert result["file"]["content_base64"] == "AAAA"
        client.file.get_file_info_legacy.assert_called_once_with(
            file_phid="PHID-FILE-abc"
        )


class TestPhaFileInfo:
    def test_info_by_monogram(self, tools):
        functions, client = tools
        client.file.get_file_info_legacy.return_value = {"id": 5}

        result = functions["pha_file_info"](file="F5")

        assert result["success"] is True
        assert result["file"] == {"id": 5}


class TestPhaFileSearch:
    def test_search_with_name(self, tools):
        functions, client = tools
        client.file.search_files.return_value = {"data": []}

        result = functions["pha_file_search"](name_contains="report")

        assert result["success"] is True
        client.file.search_files.assert_called_once_with(
            constraints={"name": "report"},
            order=None,
            after=None,
            limit=100,
        )

    def test_search_with_author(self, tools):
        functions, client = tools
        client.file.search_files.return_value = {"data": []}

        functions["pha_file_search"](author_phid="PHID-USER-1", limit=10)

        client.file.search_files.assert_called_once_with(
            constraints={"authorPHIDs": ["PHID-USER-1"]},
            order=None,
            after=None,
            limit=10,
        )

    def test_search_empty_constraints(self, tools):
        functions, client = tools
        client.file.search_files.return_value = {"data": []}

        functions["pha_file_search"]()

        client.file.search_files.assert_called_once_with(
            constraints={}, order=None, after=None, limit=100
        )


class TestPhaTaskCreateWithFiles:
    def test_no_file_phids_unchanged(self, tools):
        functions, client = tools
        client.maniphest.create_task.return_value = {"id": 1}

        functions["pha_task_create"](title="t", description="body")

        client.maniphest.create_task.assert_called_once_with(
            title="t", description="body", owner_phid=""
        )

    def test_appends_file_refs_to_description(self, tools):
        functions, client = tools
        client.maniphest.create_task.return_value = {"id": 1}

        functions["pha_task_create"](
            title="t", description="body", file_phids=["F42"]
        )

        client.maniphest.create_task.assert_called_once_with(
            title="t", description="body\n\n{F42}", owner_phid=""
        )

    def test_idempotent_when_ref_already_present(self, tools):
        functions, client = tools
        client.maniphest.create_task.return_value = {"id": 1}

        functions["pha_task_create"](
            title="t",
            description="see {F42}",
            file_phids=["F42"],
        )

        client.maniphest.create_task.assert_called_once_with(
            title="t", description="see {F42}", owner_phid=""
        )


class TestPhaTaskUpdateWithFiles:
    def test_no_file_phids_unchanged(self, tools):
        functions, client = tools

        functions["pha_task_update"](task_id="T1", title="new")

        client.maniphest.edit_task.assert_called_once()

    def test_file_phids_with_description_appended(self, tools):
        functions, client = tools

        functions["pha_task_update"](
            task_id="T1",
            description="body",
            file_phids=["F7"],
        )

        # Capture the transactions passed to edit_task.
        call = client.maniphest.edit_task.call_args
        transactions = call.kwargs["transactions"]
        desc_txns = [
            txn for txn in transactions if txn["type"] == "description"
        ]
        assert len(desc_txns) == 1
        assert desc_txns[0]["value"] == "body\n\n{F7}"

    def test_file_phids_without_description_raises(self, tools):
        functions, _ = tools

        result = functions["pha_task_update"](
            task_id="T1", status="resolved", file_phids=["F7"]
        )

        assert result["success"] is False
        assert "description" in result["error"]
        assert result["error_code"] == "VALIDATION_ERROR"


class TestPhaTaskAddCommentWithFiles:
    def test_no_file_phids_unchanged(self, tools):
        functions, client = tools

        functions["pha_task_add_comment"](task_id="T1", comment="hi")

        call = client.maniphest.edit_task.call_args
        txns = call.kwargs["transactions"]
        assert txns[0]["value"] == "hi"

    def test_appends_file_refs(self, tools):
        functions, client = tools

        functions["pha_task_add_comment"](
            task_id="T1", comment="see this", file_phids=["F5"]
        )

        txns = client.maniphest.edit_task.call_args.kwargs["transactions"]
        assert txns[0]["value"] == "see this\n\n{F5}"

    def test_idempotent_when_present(self, tools):
        functions, client = tools

        functions["pha_task_add_comment"](
            task_id="T1", comment="see {F5}", file_phids=["F5"]
        )

        txns = client.maniphest.edit_task.call_args.kwargs["transactions"]
        assert txns[0]["value"] == "see {F5}"


class TestPhaDiffAddCommentWithFiles:
    def test_no_file_phids_unchanged(self, tools):
        functions, client = tools

        functions["pha_diff_add_comment"](
            revision_id="D1", comment="hi"
        )

        txns = client.differential.edit_revision.call_args.kwargs[
            "transactions"
        ]
        comment_txn = next(t for t in txns if t["type"] == "comment")
        assert comment_txn["value"] == "hi"

    def test_appends_file_refs(self, tools):
        functions, client = tools

        functions["pha_diff_add_comment"](
            revision_id="D1",
            comment="see this",
            file_phids=["F11"],
        )

        txns = client.differential.edit_revision.call_args.kwargs[
            "transactions"
        ]
        comment_txn = next(t for t in txns if t["type"] == "comment")
        assert comment_txn["value"] == "see this\n\n{F11}"

    def test_idempotent_when_present(self, tools):
        functions, client = tools

        functions["pha_diff_add_comment"](
            revision_id="D1",
            comment="see {F11}",
            file_phids=["F11"],
        )

        txns = client.differential.edit_revision.call_args.kwargs[
            "transactions"
        ]
        comment_txn = next(t for t in txns if t["type"] == "comment")
        assert comment_txn["value"] == "see {F11}"
