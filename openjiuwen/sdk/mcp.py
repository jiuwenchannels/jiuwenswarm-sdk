"""SDK MCP Server façade — expose JiuwenSwarm agents via the Model Context Protocol.

The :class:`MCPServer` turns one or more agents into MCP-compatible tool
endpoints that any MCP client (Claude Desktop, Cursor, …) can discover and
call.

Quick start::

    from openjiuwen.sdk.mcp import MCPServer

    server = MCPServer(agents=[agent1, agent2])
    await server.start(host="localhost", port=9000)
    # … serve requests …
    await server.stop()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from openjiuwen.sdk._internal import mcp_bridge as _mb

if TYPE_CHECKING:
    from openjiuwen.sdk.agent import Agent


# ---------------------------------------------------------------------------
# MCPServer façade
# ---------------------------------------------------------------------------


class MCPServer:
    """Exposes a list of :class:`~openjiuwen.sdk.agent.Agent` instances as MCP endpoints.

    Implements the MCP stdio JSON-RPC protocol.  After :meth:`start` the server
    accepts inbound connections and routes ``tools/call`` requests to the
    appropriate agent.

    Example::

        server = MCPServer(agents=[support_agent, coding_agent])
        await server.start("localhost", 9000)
        # … block while serving …
        await server.stop()
    """

    def __init__(self, agents: list["Agent"]) -> None:
        if not agents:
            raise ValueError("MCPServer requires at least one agent.")
        self._agents = agents
        self._server: Any = _mb.build_mcp_server(agents)
        self._running = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self, host: str = "localhost", port: int = 9000) -> None:
        """Start the MCP server.

        Args:
            host: Host to bind to (default: ``"localhost"``).
            port: Port to bind to (default: ``9000``).
        """
        await _mb.start_mcp_server(self._server, host, port)
        self._running = True

    async def stop(self) -> None:
        """Stop the MCP server and release resources."""
        await _mb.stop_mcp_server(self._server)
        self._running = False

    # ------------------------------------------------------------------
    # Request routing
    # ------------------------------------------------------------------

    async def handle(self, method: str, params: dict[str, Any]) -> Any:
        """Route a raw MCP JSON-RPC *method* call (for embedded use).

        Args:
            method: JSON-RPC method name (e.g. ``"tools/call"``).
            params: JSON-RPC parameters dict.

        Returns:
            The JSON-RPC response dict.
        """
        return await _mb.route_mcp_request(self._server, method, params)

    # ------------------------------------------------------------------
    # Context manager support
    # ------------------------------------------------------------------

    async def __aenter__(self) -> "MCPServer":
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.stop()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def running(self) -> bool:
        """``True`` if the server is currently running."""
        return self._running

    @property
    def agent_count(self) -> int:
        """Number of agents exposed by this server."""
        return len(self._agents)

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"MCPServer(agents={len(self._agents)}, running={self._running})"
        )
