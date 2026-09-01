"""Mock-based tests for ``pha_task_update_relationships``.

Regression coverage for the destructive default: adding a subtask used to
emit ``subtasks.set``, which replaces the entire edge list and so silently
removed every pre-existing subtask.

Fixture identifiers here are synthetic - the assertions depend only on the
transaction type that gets emitted, never on any real object.
"""

from unittest.mock import MagicMock

import pytest

from conduit.main_tools import register_tools


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


def sent_transactions(client):
    """Return the transaction list passed to the last ``edit_task`` call."""
    return client.maniphest.edit_task.call_args.kwargs["transactions"]


class TestSubtaskMode:
    def test_default_mode_is_additive(self, tools):
        """No explicit mode must NOT replace the existing subtask list."""
        funcs, client = tools

        funcs["pha_task_update_relationships"](
            task_id="PHID-TASK-parent",
            relationship_type="subtask",
            target_ids="PHID-TASK-new",
        )

        assert sent_transactions(client) == [
            {"type": "subtasks.add", "value": ["PHID-TASK-new"]}
        ]

    def test_remove_mode(self, tools):
        funcs, client = tools

        funcs["pha_task_update_relationships"](
            task_id="PHID-TASK-parent",
            relationship_type="subtask",
            target_ids="PHID-TASK-old",
            mode="remove",
        )

        assert sent_transactions(client) == [
            {"type": "subtasks.remove", "value": ["PHID-TASK-old"]}
        ]

    def test_set_mode_still_available(self, tools):
        """Whole-list replacement stays reachable, but only on request."""
        funcs, client = tools

        funcs["pha_task_update_relationships"](
            task_id="PHID-TASK-parent",
            relationship_type="subtask",
            target_ids="PHID-TASK-a,PHID-TASK-b",
            mode="set",
        )

        assert sent_transactions(client) == [
            {"type": "subtasks.set", "value": ["PHID-TASK-a", "PHID-TASK-b"]}
        ]


class TestParentMode:
    def test_default_mode_is_additive(self, tools):
        funcs, client = tools

        funcs["pha_task_update_relationships"](
            task_id="PHID-TASK-child",
            relationship_type="parent",
            target_ids="PHID-TASK-new-parent",
        )

        assert sent_transactions(client) == [
            {"type": "parents.add", "value": ["PHID-TASK-new-parent"]}
        ]

    def test_remove_mode(self, tools):
        funcs, client = tools

        funcs["pha_task_update_relationships"](
            task_id="PHID-TASK-child",
            relationship_type="parent",
            target_ids="PHID-TASK-old-parent",
            mode="remove",
        )

        assert sent_transactions(client) == [
            {"type": "parents.remove", "value": ["PHID-TASK-old-parent"]}
        ]


class TestValidation:
    def test_invalid_mode_rejected_without_calling_api(self, tools):
        funcs, client = tools

        result = funcs["pha_task_update_relationships"](
            task_id="PHID-TASK-parent",
            relationship_type="subtask",
            target_ids="PHID-TASK-new",
            mode="replace",
        )

        assert result["success"] is False
        # Must be our own validation message naming the valid modes, not a
        # TypeError swallowed by @handle_api_errors.
        assert "Invalid mode" in result["error"]
        for valid in ("add", "remove", "set"):
            assert valid in result["error"]
        client.maniphest.edit_task.assert_not_called()

    def test_invalid_relationship_type_rejected(self, tools):
        funcs, client = tools

        result = funcs["pha_task_update_relationships"](
            task_id="PHID-TASK-parent",
            relationship_type="cousin",
            target_ids="PHID-TASK-new",
        )

        assert result["success"] is False
        client.maniphest.edit_task.assert_not_called()

    def test_empty_targets_rejected(self, tools):
        funcs, client = tools

        result = funcs["pha_task_update_relationships"](
            task_id="PHID-TASK-parent",
            relationship_type="subtask",
            target_ids="  ,  ",
        )

        assert result["success"] is False
        client.maniphest.edit_task.assert_not_called()


class TestDestructiveDefaultRegression:
    def test_adding_subtasks_never_emits_set(self, tools):
        """A parent already holding many subtasks gains a few more, and the
        caller lists only the new ones. No transaction may carry ``set``
        semantics - ``set`` would drop every subtask not listed."""
        funcs, client = tools

        funcs["pha_task_update_relationships"](
            task_id="PHID-TASK-parent",
            relationship_type="subtask",
            target_ids=(
                "PHID-TASK-new-1,PHID-TASK-new-2,PHID-TASK-new-3"
            ),
        )

        types = [tx["type"] for tx in sent_transactions(client)]
        assert types == ["subtasks.add"]
        assert not any(t.endswith(".set") for t in types)
