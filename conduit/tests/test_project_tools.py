"""Mock-based tests for cursor pagination on ``pha_project_search``.

These tests register tools against the shared :class:`CapturingMCP` stub
(see ``conduit/tests/conftest.py``) and exercise the resulting function
directly, mocking the underlying ``PhabricatorClient`` rather than the
FastMCP server itself.
"""


class TestPhaProjectSearch:
    def test_forwards_after_and_order(self, tools):
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
