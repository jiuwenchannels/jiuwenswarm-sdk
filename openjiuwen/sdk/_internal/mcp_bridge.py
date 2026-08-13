"""MCP (Model Context Protocol) bridge.

Module-level patchable functions that wrap ``openjiuwen.agent_teams.mcp``
primitives behind the SDK surface.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Module-level patchable callables
# ---------------------------------------------------------------------------


def build_mcp_server(agents: list[Any]) -> Any:
    """Build an MCP server instance from a list of agents (patchable)."""
    try:
        from openjiuwen.agent_teams.mcp import build_server

        return build_server(agents=agents)
    except ImportError:
        return _FallbackMCPServer(agents=agents)


async def start_mcp_server(server: Any, host: str, port: int) -> None:
    """Start *server* on *host*:*port* (patchable)."""
    if isinstance(server, _FallbackMCPServer):
        await server.start(host, port)
        return
    try:
        if hasattr(server, "start"):
            await server.start(host=host, port=port)
    except Exception as exc:  # noqa: BLE001
        from openjiuwen.sdk.errors import SdkError

        raise SdkError(f"MCPServer.start failed: {exc}") from exc


async def stop_mcp_server(server: Any) -> None:
    """Stop *server* (patchable)."""
    if isinstance(server, _FallbackMCPServer):
        await server.stop()
        return
    try:
        if hasattr(server, "stop"):
            await server.stop()
    except Exception:  # noqa: BLE001
        pass


async def route_mcp_request(
    server: Any, method: str, params: dict[str, Any]
) -> Any:
    """Route an MCP JSON-RPC request through *server* (patchable)."""
    if isinstance(server, _FallbackMCPServer):
        return await server.handle(method, params)
    try:
        return await server.route(method=method, params=params)
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Fallback
# ---------------------------------------------------------------------------


class _FallbackMCPServer:
    """Stub MCP server used when the runtime package is not installed."""

    def __init__(self, agents: list[Any]) -> None:
        self._agents = agents
        self._running = False

    async def start(self, host: str, port: int) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False

    async def handle(self, method: str, params: dict[str, Any]) -> Any:
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "jiuwenswarm-mcp", "version": "1.0.0"},
                    "capabilities": {"tools": {}},
                },
            }
        if method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "result": {
                    "tools": [
                        {
                            "name": "jiuwenswarm_run",
                            "description": "Run a JiuwenSwarm agent.",
                            "inputSchema": {
                                "type": "object",
                                "properties": {
                                    "prompt": {"type": "string"},
                                    "session_id": {"type": "string"},
                                },
                                "required": ["prompt"],
                            },
                        }
                    ]
                },
            }
        if method == "tools/call":
            tool_name = params.get("name", "")
            args = params.get("arguments", {})
            if tool_name == "jiuwenswarm_run" and self._agents:
                agent = self._agents[0]
                prompt = args.get("prompt", "")
                try:
                    result = await agent.run(prompt)
                    return {"jsonrpc": "2.0", "result": {"content": [{"type": "text", "text": result.text}]}}
                except Exception as exc:  # noqa: BLE001
                    return {"jsonrpc": "2.0", "error": {"code": -1, "message": str(exc)}}
        return {"jsonrpc": "2.0", "error": {"code": -32601, "message": f"Method not found: {method}"}}
