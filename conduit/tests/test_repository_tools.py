"""Mock-based tests for cursor pagination on repository search tools.

These tests register tools against the shared :class:`CapturingMCP` stub
(see ``conduit/tests/conftest.py``) and exercise the resulting functions
directly, mocking the underlying ``PhabricatorClient`` rather than the
FastMCP server itself.
"""


class TestPhaRepositorySearch:
    def test_forwards_after_and_order(self, tools):
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


class TestPhaRepositoryCommitsSearch:
    def test_forwards_after_and_order(self, tools):
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
