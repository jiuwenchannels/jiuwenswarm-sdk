"""17_a2a_server_and_client.py — expose an agent over A2A and call it remotely.

Corresponds to §17 of the usage examples.

Shows:
  - A2AServer: exposing a local agent over JSON-RPC
  - RemoteAgent.connect(): calling a remote A2A agent from Python
  - Streaming from a remote A2A agent
  - Composing local + remote agents into a Team

Run (server):
    python examples/17_a2a_server_and_client.py --mode server

Run (client, after starting the server):
    python examples/17_a2a_server_and_client.py --mode client
"""

import asyncio
import os
import sys

from openjiuwen.sdk import Agent, Team, ModelConfig
from openjiuwen.sdk.a2a import A2AServer, RemoteAgent


# ---------------------------------------------------------------------------
# Server side — expose an agent over A2A
# ---------------------------------------------------------------------------

async def run_server():
    agent = await Agent.create("specialist", model=ModelConfig.from_env())

    server = A2AServer(
        agent=agent,
        interface_url="http://10.0.1.5:9000",
        host="0.0.0.0",
        port=9000,
    )
    print("A2A server listening on :9000")
    await server.serve_forever()


# ---------------------------------------------------------------------------
# Client side — call the remote agent
# ---------------------------------------------------------------------------

async def run_client():
    # Connect to the remote agent by URL — A2A uses JSON-RPC, not the WS gateway.
    remote = await RemoteAgent.connect(
        "http://10.0.1.5:9000",
        auth_token=os.environ.get("JIUWENSWARM_TOKEN"),
    )

    # Use exactly like a local agent
    result = await remote.run("Analyse the dataset and return a summary.")
    print(result.text)

    # Streaming works too
    async for token in remote.stream("Write a report on the findings."):
        print(token, end="", flush=True)
    print()


# ---------------------------------------------------------------------------
# Compose local and remote agents into a team
# ---------------------------------------------------------------------------

async def local_and_remote_team():
    model_cfg = ModelConfig.from_env()
    local_writer = await Agent.create("writer", model=model_cfg)
    remote_analyst = await RemoteAgent.connect(
        "http://10.0.1.5:9000",
        auth_token=os.environ.get("JIUWENSWARM_TOKEN"),
    )

    team = await Team.create(agents=[local_writer, remote_analyst], model=model_cfg)
    result = await team.spawn("Analyse sales data and write an executive summary.")
    print(result.final_output)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "client"
    if mode == "--mode=server" or mode == "server":
        asyncio.run(run_server())
    else:
        asyncio.run(run_client())
