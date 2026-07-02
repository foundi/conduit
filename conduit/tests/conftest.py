"""Shared pytest fixtures for MCP tool tests.

``tools`` registers the tools module against a lightweight stand-in for
``FastMCP`` and hands back the resulting functions plus a mocked
``PhabricatorClient``, so individual test files can exercise a tool
function directly without a live Phorge instance.
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
