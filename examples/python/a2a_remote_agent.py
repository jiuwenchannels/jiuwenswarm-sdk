"""a2a_remote_agent.py — call a remote JiuwenSwarm agent via the A2A protocol.

Shows:
  - Connecting to a remote agent service
  - Blocking run() call
  - Token-by-token stream() call
  - Cancelling a task
  - Composing local + remote agents into a Team

The remote service must expose a JiuwenSwarm A2A endpoint.
If no service is running the examples print connection-failure messages
and continue — no crash.

Run:
    python examples/a2a_remote_agent.py
"""

import asyncio

from openjiuwen.sdk import Agent, ModelConfig, RemoteAgent
from openjiuwen.sdk.errors import ConnectionError


REMOTE_URL = "http://localhost:9001"   # change to your A2A service URL
AGENT_ID   = "summariser"             # agent registered on that service


# ---------------------------------------------------------------------------
# Basic run
# ---------------------------------------------------------------------------

async def basic_run_demo() -> None:
    print("=== Basic A2A run ===")
    agent = RemoteAgent(REMOTE_URL, AGENT_ID, timeout=30.0)
    try:
        result = await agent.run("Summarise the CAP theorem in one sentence.")
        print(f"Result: {result.text}")
        print(f"Task ID: {result.task_id}")
    except ConnectionError as exc:
        print(f"[not connected — {exc}]")
    finally:
        await agent.close()


# ---------------------------------------------------------------------------
# Streaming
# ---------------------------------------------------------------------------

async def streaming_demo() -> None:
    print("\n=== A2A streaming ===")
    async with RemoteAgent(REMOTE_URL, AGENT_ID) as agent:
        try:
            print("Tokens: ", end="")
            async for token in agent.stream("Write a haiku about latency."):
                print(token, end="", flush=True)
            print()
        except ConnectionError as exc:
            print(f"[not connected — {exc}]")


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------

async def cancel_demo() -> None:
    print("\n=== A2A cancel ===")
    async with RemoteAgent(REMOTE_URL, AGENT_ID) as agent:
        try:
            # In a real use case you'd capture task_id from a run() call
            # and cancel it from another coroutine or thread.
            ok = await agent.cancel("task-example-123")
            print(f"Cancelled: {ok}")
        except ConnectionError as exc:
            print(f"[not connected — {exc}]")


# ---------------------------------------------------------------------------
# Compose local + remote into a team
# ---------------------------------------------------------------------------

async def local_plus_remote_team() -> None:
    """
    One local agent plans the work; a remote agent executes the summarisation.
    The results are combined by the local agent.
    """
    print("\n=== Local + remote composition ===")

    remote = RemoteAgent(REMOTE_URL, AGENT_ID)

    try:
        # 1. Local agent plans
        local = await Agent.create("planner", model=ModelConfig.from_env())
        plan = await local.run("List two topics worth researching about WebAssembly.")

        # 2. Remote agent summarises each topic
        for line in plan.text.strip().splitlines()[:2]:
            topic = line.strip("- ").strip()
            if not topic:
                continue
            try:
                summary = await remote.run(f"Summarise: {topic}")
                print(f"  [{topic[:30]}…] → {summary.text[:80]}…")
            except ConnectionError:
                print(f"  [{topic[:30]}…] → [remote unavailable]")
    finally:
        await remote.close()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    await basic_run_demo()
    await streaming_demo()
    await cancel_demo()
    await local_plus_remote_team()


if __name__ == "__main__":
    asyncio.run(main())
