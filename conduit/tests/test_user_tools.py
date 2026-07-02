"""Mock-based tests for cursor pagination on ``pha_user_search``.

These tests register tools against the shared :class:`CapturingMCP` stub
(see ``conduit/tests/conftest.py``) and exercise the resulting function
directly, mocking the underlying ``PhabricatorClient`` rather than the
FastMCP server itself.
"""


class TestPhaUserSearch:
    def test_forwards_after_and_order(self, tools):
        functions, client = tools
        client.user.search.return_value = {
            "data": [], "cursor": {"after": None}
        }

        functions["pha_user_search"](after="cursor-x", order="newest")

        kwargs = client.user.search.call_args.kwargs
        assert kwargs["after"] == "cursor-x"
        assert kwargs["order"] == "newest"

    def test_returns_after_when_cursor_has_it(self, tools):
        functions, client = tools
        client.user.search.return_value = {
            "data": [], "cursor": {"after": "abc", "limit": 100}
        }

        result = functions["pha_user_search"]()

        assert result["next_after"] == "abc"

    def test_returns_none_when_cursor_after_is_none(self, tools):
        functions, client = tools
        client.user.search.return_value = {
            "data": [], "cursor": {"after": None}
        }

        result = functions["pha_user_search"]()

        assert result["next_after"] is None

    def test_keeps_legacy_users_and_cursor(self, tools):
        functions, client = tools
        client.user.search.return_value = {
            "data": [{"phid": "PHID-USER-1"}],
            "cursor": {"after": None, "limit": 100},
        }

        result = functions["pha_user_search"]()

        assert result["users"] == [{"phid": "PHID-USER-1"}]
        assert result["cursor"] == {"after": None, "limit": 100}
