"""Mock-based tests for cursor pagination on ``pha_task_search_advanced``.

These tests register tools against the shared :class:`CapturingMCP` stub
(see ``conduit/tests/conftest.py``) and exercise the resulting function
directly, mocking the underlying ``PhabricatorClient`` rather than the
FastMCP server itself.
"""


class TestPhaTaskSearchAdvanced:
    def test_forwards_after_and_order(self, tools):
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
