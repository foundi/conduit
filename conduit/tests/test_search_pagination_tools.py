"""Mock-based tests for cursor pagination on search MCP tools.

These tests register tools against a lightweight :class:`CapturingMCP` and
exercise the resulting functions directly, mocking the underlying
``PhabricatorClient`` rather than the FastMCP server itself.
"""

from unittest.mock import MagicMock

import pytest

from conduit.main_tools import (
    _cursor_next_after,
    _paged_search_response,
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


class TestForwardingAfterAndOrder:
    def test_user_search_forwards_after_and_order(self, tools):
        functions, client = tools
        client.user.search.return_value = {
            "data": [], "cursor": {"after": None}
        }

        functions["pha_user_search"](after="cursor-x", order="newest")

        kwargs = client.user.search.call_args.kwargs
        assert kwargs["after"] == "cursor-x"
        assert kwargs["order"] == "newest"

    def test_task_search_advanced_forwards_after_and_order(self, tools):
        functions, client = tools
        client.maniphest.search_tasks.return_value = {
            "data": [], "cursor": {"after": None}
        }

        functions["pha_task_search_advanced"](
            after="cursor-x", order="newest"
        )

        kwargs = client.maniphest.search_tasks.call_args.kwargs
        assert kwargs["after"] == "cursor-x"
        assert kwargs["order"] == "newest"

    def test_repository_search_forwards_after_and_order(self, tools):
        functions, client = tools
        client.diffusion.search_repositories.return_value = {
            "data": [], "cursor": {"after": None}
        }

        functions["pha_repository_search"](
            after="cursor-x", order="newest"
        )

        kwargs = client.diffusion.search_repositories.call_args.kwargs
        assert kwargs["after"] == "cursor-x"
        assert kwargs["order"] == "newest"

    def test_repository_commits_search_forwards_after_and_order(
        self, tools
    ):
        functions, client = tools
        client.diffusion.search_commits.return_value = {
            "data": [], "cursor": {"after": None}
        }

        functions["pha_repository_commits_search"](
            after="cursor-x", order="newest"
        )

        kwargs = client.diffusion.search_commits.call_args.kwargs
        assert kwargs["after"] == "cursor-x"
        assert kwargs["order"] == "newest"

    def test_diff_search_forwards_after_and_order(self, tools):
        functions, client = tools
        client.differential.search_revisions.return_value = {
            "data": [], "cursor": {"after": None}
        }

        functions["pha_diff_search"](after="cursor-x", order="newest")

        kwargs = client.differential.search_revisions.call_args.kwargs
        assert kwargs["after"] == "cursor-x"
        assert kwargs["order"] == "newest"

    def test_file_search_forwards_after_and_order(self, tools):
        functions, client = tools
        client.file.search_files.return_value = {
            "data": [], "cursor": {"after": None}
        }

        functions["pha_file_search"](after="cursor-x", order="newest")

        kwargs = client.file.search_files.call_args.kwargs
        assert kwargs["after"] == "cursor-x"
        assert kwargs["order"] == "newest"

    def test_file_search_converts_empty_after_and_order_to_none(
        self, tools
    ):
        functions, client = tools
        client.file.search_files.return_value = {
            "data": [], "cursor": {"after": None}
        }

        functions["pha_file_search"]()

        kwargs = client.file.search_files.call_args.kwargs
        assert kwargs["order"] is None
        assert kwargs["after"] is None

    def test_project_search_forwards_after_and_order(self, tools):
        functions, client = tools
        client.project.search_projects.return_value = {
            "data": [], "cursor": {"after": None}
        }

        functions["pha_project_search"](
            after="cursor-x", order="newest"
        )

        kwargs = client.project.search_projects.call_args.kwargs
        assert kwargs["after"] == "cursor-x"
        assert kwargs["order"] == "newest"

    def test_workboard_search_columns_forwards_after_and_order(
        self, tools
    ):
        functions, client = tools
        client.project.search_columns.return_value = {
            "data": [], "cursor": {"after": None}
        }

        functions["pha_workboard_search_columns"](
            after="cursor-x", order="newest"
        )

        kwargs = client.project.search_columns.call_args.kwargs
        assert kwargs["after"] == "cursor-x"
        assert kwargs["order"] == "newest"

    def test_workboard_search_tasks_by_column_forwards_after_and_order(
        self, tools
    ):
        functions, client = tools
        client.maniphest.search_tasks.return_value = {
            "data": [], "cursor": {"after": None}
        }

        functions["pha_workboard_search_tasks_by_column"](
            column_phid="PHID-PCOL-1", after="cursor-x", order="newest"
        )

        kwargs = client.maniphest.search_tasks.call_args.kwargs
        assert kwargs["after"] == "cursor-x"
        assert kwargs["order"] == "newest"


class TestNextAfterExtraction:
    def test_file_search_returns_after_when_cursor_has_it(self, tools):
        functions, client = tools
        client.file.search_files.return_value = {
            "data": [], "cursor": {"after": "abc", "limit": 100}
        }

        result = functions["pha_file_search"]()

        assert result["next_after"] == "abc"

    def test_file_search_returns_none_when_cursor_after_is_none(
        self, tools
    ):
        functions, client = tools
        client.file.search_files.return_value = {
            "data": [], "cursor": {"after": None}
        }

        result = functions["pha_file_search"]()

        assert result["next_after"] is None

    def test_file_search_returns_none_when_cursor_key_missing(
        self, tools
    ):
        functions, client = tools
        client.file.search_files.return_value = {"data": []}

        result = functions["pha_file_search"]()

        assert result["next_after"] is None

    def test_user_search_returns_after_when_cursor_has_it(self, tools):
        functions, client = tools
        client.user.search.return_value = {
            "data": [], "cursor": {"after": "abc", "limit": 100}
        }

        result = functions["pha_user_search"]()

        assert result["next_after"] == "abc"

    def test_user_search_returns_none_when_cursor_after_is_none(
        self, tools
    ):
        functions, client = tools
        client.user.search.return_value = {
            "data": [], "cursor": {"after": None}
        }

        result = functions["pha_user_search"]()

        assert result["next_after"] is None


class TestEnvelopeCompatibility:
    def test_diff_search_keeps_legacy_revisions_and_pagination(
        self, tools
    ):
        functions, client = tools
        client.differential.search_revisions.return_value = {
            "data": [{"id": 1}], "cursor": {"after": "xyz", "limit": 50}
        }

        result = functions["pha_diff_search"]()

        assert result["success"] is True
        assert result["revisions"]["data"] == [{"id": 1}]
        assert result["revisions"]["pagination"]["cursor"] == {
            "after": "xyz", "limit": 50
        }

    def test_user_search_keeps_legacy_users_and_cursor(self, tools):
        functions, client = tools
        client.user.search.return_value = {
            "data": [{"phid": "PHID-USER-1"}],
            "cursor": {"after": None, "limit": 100},
        }

        result = functions["pha_user_search"]()

        assert result["users"] == [{"phid": "PHID-USER-1"}]
        assert result["cursor"] == {"after": None, "limit": 100}


class TestCursorNextAfter:
    def test_returns_after_when_present(self):
        assert _cursor_next_after({"cursor": {"after": "abc"}}) == "abc"

    def test_returns_none_when_after_is_none(self):
        assert _cursor_next_after({"cursor": {"after": None}}) is None

    def test_returns_none_when_cursor_missing(self):
        assert _cursor_next_after({"data": []}) is None


class TestPagedSearchResponse:
    def test_builds_success_envelope_with_key_and_next_after(self):
        result = _paged_search_response(
            "files", {"data": [], "cursor": {"after": "abc", "limit": 100}}
        )

        assert result["success"] is True
        assert result["files"]["data"] == []
        assert result["next_after"] == "abc"

    def test_injects_pagination_block_into_result(self):
        result = _paged_search_response(
            "files", {"data": [], "cursor": {"after": "abc", "limit": 100}}
        )

        assert result["files"]["pagination"] == {
            "cursor": {"after": "abc", "limit": 100},
            "has_more": True,
            "limit": 100,
        }

    def test_next_after_is_none_when_cursor_missing(self):
        result = _paged_search_response("files", {"data": []})

        assert result["next_after"] is None
        assert "pagination" not in result["files"]
