"""quick_start.py — the 10-line hello world for JiuwenSwarm.

Shows both execution modes:
  - In-process: runtime runs inside this process (requires openjiuwen package)
  - Remote:     runtime runs in a separate server (only SDK needed)

Run:
    python examples/quick_start.py

Environment variables:
    JIUWENSWARM_API_KEY   your OpenAI / Anthropic key (in-process mode)
    JIUWENSWARM_MODEL     model name (default: gpt-4o)
    JIUWENSWARM_URL       server URL (remote mode, default: ws://localhost:19000/v1/ws)
    JIUWENSWARM_TOKEN     auth token (remote mode, optional in dev)
"""

import asyncio

from openjiuwen.sdk import Agent, ModelConfig, RemoteConfig


# ---------------------------------------------------------------------------
# In-process mode
# ---------------------------------------------------------------------------

async def inprocess_example() -> None:
    """Run an agent whose LLM calls happen inside this process."""
    agent = await Agent.create(
        "researcher",
        model=ModelConfig(
            provider="openai",
            model="gpt-4o",
            api_key="sk-your-key-here",   # or set JIUWENSWARM_API_KEY
        ),
    )

    result = await agent.run("Explain the CAP theorem in two sentences.")
    print("In-process result:")
    print(result.text)
    print(f"Session: {result.session_id}")


# ---------------------------------------------------------------------------
# In-process — sync variant (no event loop needed)
# ---------------------------------------------------------------------------

def sync_example() -> None:
    """Works in scripts with no async context."""
    agent = Agent.create_sync(
        "helper",
        model=ModelConfig.from_env(),  # reads JIUWENSWARM_* env vars
    )
    result = agent.run_sync("What is 7 times 8?")
    print("Sync result:", result.text)


# ---------------------------------------------------------------------------
# Remote mode
# ---------------------------------------------------------------------------

async def remote_example() -> None:
    """Connect to a running JiuwenSwarm server — no runtime needed locally."""
    # Using RemoteConfig for full control
    config = RemoteConfig(
        server_url="ws://localhost:19000/v1/ws",
        auth_token=None,  # leave None in dev
        timeout=60.0,
    )

    try:
        agent = await Agent.connect(
            config.server_url,
            auth_token=config.auth_token,
            config=config,
        )
        result = await agent.run("What is the capital of France?")
        print("Remote result:", result.text)
        await agent.close()
    except Exception as exc:
        print(f"Remote connection failed (server not running?): {exc}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Choose which example to run:
    print("=== In-process (sync) ===")
    # sync_example()       # uncomment after setting JIUWENSWARM_API_KEY

    print("=== Remote ===")
    asyncio.run(remote_example())
