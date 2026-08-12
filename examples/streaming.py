"""streaming.py — stream tokens as the model generates them.

Two styles:
  1. async-for loop  — process each token inline
  2. event callbacks — register handlers with agent.on()

Run:
    python examples/streaming.py
"""

import asyncio

from openjiuwen.sdk import Agent, ModelConfig


PROMPT = "Write a short poem about distributed systems."


# ---------------------------------------------------------------------------
# Style 1 — async-for loop
# ---------------------------------------------------------------------------

async def stream_with_loop(agent: Agent) -> None:
    print("── async-for loop ──────────────────────────")
    async for token in agent.stream(PROMPT):
        print(token, end="", flush=True)
    print()   # newline after stream


# ---------------------------------------------------------------------------
# Style 2 — event callbacks
# ---------------------------------------------------------------------------

async def stream_with_events(agent: Agent) -> None:
    print("── event callbacks ─────────────────────────")
    received: list[str] = []

    agent.on("token", lambda t: received.append(t))
    agent.on("done", lambda: print(f"\n[done — {len(received)} tokens]"))

    # Consume the generator (events fire as tokens arrive)
    async for _ in agent.stream(PROMPT):
        pass

    # Remove listeners so they don't fire in subsequent calls
    agent.off_all("token")
    agent.off_all("done")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    agent = await Agent.create(
        "poet",
        model=ModelConfig.from_env(),
    )

    await stream_with_loop(agent)
    await stream_with_events(agent)


if __name__ == "__main__":
    asyncio.run(main())
