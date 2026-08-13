"""Unit tests for openjiuwen.sdk.mcp — MCPServer façade."""

from __future__ import annotations

import pytest

from openjiuwen.sdk.mcp import MCPServer


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeAgent:
    """A minimal mock agent for MCPServer tests."""

    def __init__(self, name: str = "agent"):
        self.name = name

    async def run(self, prompt: str, **kwargs):
        return type("R", (), {"text": f"response from {self.name}", "session_id": None})()


# ---------------------------------------------------------------------------
# MCPServer construction
# ---------------------------------------------------------------------------


def test_mcp_server_requires_agents():
    with pytest.raises(ValueError, match="at least one agent"):
        MCPServer(agents=[])


def test_mcp_server_agent_count():
    agents = [_FakeAgent("a"), _FakeAgent("b")]
    server = MCPServer(agents=agents)
    assert server.agent_count == 2


def test_mcp_server_not_running_on_creation():
    server = MCPServer(agents=[_FakeAgent()])
    assert server.running is False


def test_mcp_server_repr():
    server = MCPServer(agents=[_FakeAgent()])
    rep = repr(server)
    assert "MCPServer" in rep
    assert "running=False" in rep


# ---------------------------------------------------------------------------
# MCPServer start / stop
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mcp_server_start_sets_running():
    server = MCPServer(agents=[_FakeAgent()])
    await server.start(host="localhost", port=19000)
    assert server.running is True
    await server.stop()


@pytest.mark.asyncio
async def test_mcp_server_stop_clears_running():
    server = MCPServer(agents=[_FakeAgent()])
    await server.start(host="localhost", port=19001)
    await server.stop()
    assert server.running is False


# ---------------------------------------------------------------------------
# MCPServer.handle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mcp_server_handle_tools_list():
    server = MCPServer(agents=[_FakeAgent("bot")])
    response = await server.handle("tools/list", {})
    # The fallback bridge returns a dict; just check it doesn't raise
    assert response is not None


@pytest.mark.asyncio
async def test_mcp_server_handle_tools_call():
    server = MCPServer(agents=[_FakeAgent("bot")])
    response = await server.handle("tools/call", {"name": "bot", "arguments": {"prompt": "Hi"}})
    assert response is not None


# ---------------------------------------------------------------------------
# MCPServer context manager
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mcp_server_context_manager():
    server = MCPServer(agents=[_FakeAgent()])
    async with server:
        pass
    assert server.running is False
