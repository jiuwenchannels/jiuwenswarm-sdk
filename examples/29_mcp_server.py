"""29_mcp_server.py — expose JiuwenSwarm agents via the MCP protocol.

Two modes:
  1. Subprocess: launch the built-in MCP server as a child process that speaks
     the MCP stdio JSON-RPC protocol.
  2. Embedded: build the MCP server programmatically and run it inside your own
     async process using the MCP stdio transport.
"""

import asyncio
import os
import subprocess


# ---------------------------------------------------------------------------
# Mode 1: subprocess
# ---------------------------------------------------------------------------

def run_mcp_subprocess() -> None:
    """Launch the JiuwenSwarm MCP server as a child process.

    The server reads OPENJIUWEN_TEAM_JOIN from the environment to discover
    the agent team.  stdin/stdout speak MCP stdio (JSON-RPC newline-delimited).
    """
    proc = subprocess.Popen(
        ["python", "-m", "openjiuwen.agent_teams.mcp"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        env={**os.environ, "OPENJIUWEN_TEAM_JOIN": "team://my-team@localhost:9000"},
    )

    # Send a JSON-RPC initialize request manually for illustration.
    import json

    initialize_request = json.dumps({
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "example-client", "version": "0.0.1"},
        },
    }) + "\n"

    proc.stdin.write(initialize_request.encode())
    proc.stdin.flush()

    response_line = proc.stdout.readline()
    response = json.loads(response_line)
    print("initialize response:", json.dumps(response, indent=2))

    # Send a tool call
    tool_call = json.dumps({
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "jiuwenswarm_run",
            "arguments": {
                "prompt": "Summarise the latest commits in this repository.",
                "session_id": "sess_abc123",
            },
        },
    }) + "\n"

    proc.stdin.write(tool_call.encode())
    proc.stdin.flush()

    result_line = proc.stdout.readline()
    result = json.loads(result_line)
    print("tool call result:", json.dumps(result, indent=2))

    proc.stdin.close()
    proc.wait()


# ---------------------------------------------------------------------------
# Mode 2: embedded async server
# ---------------------------------------------------------------------------

async def run_mcp_embedded() -> None:
    """Build the MCP server programmatically and run it in-process.

    The server is a low-level ``mcp.server.lowlevel.Server`` instance.
    The MCP stdio transport handles framing over stdin/stdout.
    """
    from openjiuwen.agent_teams.mcp import build_server
    from mcp.server.stdio import stdio_server

    server = build_server()  # reads OPENJIUWEN_TEAM_JOIN from env

    async with stdio_server() as (reader, writer):
        await server.run(reader, writer, server.create_initialization_options())


# ---------------------------------------------------------------------------
# Entry point — choose which mode to demo
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import sys

    mode = sys.argv[1] if len(sys.argv) > 1 else "subprocess"

    if mode == "subprocess":
        run_mcp_subprocess()
    elif mode == "embedded":
        asyncio.run(run_mcp_embedded())
    else:
        print(f"Unknown mode: {mode!r}.  Use 'subprocess' or 'embedded'.")
        sys.exit(1)
