"""Mock-based tests for cursor pagination on workboard search tools.

These tests register tools against the shared :class:`CapturingMCP` stub
(see ``conduit/tests/conftest.py``) and exercise the resulting functions
directly, mocking the underlying ``PhabricatorClient`` rather than the
FastMCP server itself.
"""


class TestPhaWorkboardSearchColumns:
    def test_forwards_after_and_order(self, tools):
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


class TestPhaWorkboardSearchTasksByColumn:
    def test_forwards_after_and_order(self, tools):
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
