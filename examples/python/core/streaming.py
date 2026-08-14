"""02_streaming.py — stream tokens as the model generates them.

Three styles:
  1. async-for loop  — process each token inline (plain str)
  2. event callbacks — register handlers with agent.on()
  3. typed events    — stream_events() yields StreamEvent subclasses

See ``31_stream_events.py`` for a deep dive into all event types.

Run:
    python examples/python/02_streaming.py
"""

import asyncio

from openjiuwen.sdk import (
    Agent,
    DeltaEvent,
    DoneEvent,
    ModelConfig,
    ReasoningEvent,
    StatusEvent,
    ToolCallEvent,
    ToolResultEvent,
)


PROMPT = "Write a short poem about distributed systems."


# ---------------------------------------------------------------------------
# Style 1 — async-for loop (plain str tokens)
# ---------------------------------------------------------------------------

async def stream_with_loop(agent: Agent) -> None:
    print("── Style 1: async-for loop (str) ───────────────────────────────────")
    async for token in agent.stream(PROMPT):
        print(token, end="", flush=True)
    print()   # newline after stream


# ---------------------------------------------------------------------------
# Style 2 — event callbacks via agent.on()
# ---------------------------------------------------------------------------

async def stream_with_events(agent: Agent) -> None:
    print("── Style 2: event callbacks ─────────────────────────────────────────")
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
# Style 3 — typed StreamEvent objects via stream_events()
# ---------------------------------------------------------------------------

async def stream_with_typed_events(agent: Agent) -> None:
    """Yield typed events — useful when you need more than plain text.

    Unlike ``stream()`` which only yields ``str`` tokens, ``stream_events()``
    surfaces reasoning tokens, status updates, and tool interactions.
    """
    print("── Style 3: typed stream_events() ──────────────────────────────────")

    async for event in agent.stream_events(PROMPT):
        if isinstance(event, DeltaEvent):
            print(event.delta, end="", flush=True)

        elif isinstance(event, ReasoningEvent):
            # Only from models with extended thinking (o3, Claude 3.7+)
            print(f"[thinking] {event.delta}", end="", flush=True)

        elif isinstance(event, StatusEvent):
            if not event.is_complete:
                print(f"\n[…] {event.status}")

        elif isinstance(event, ToolCallEvent):
            print(f"\n[→ tool] {event.tool_name}({event.arguments})")

        elif isinstance(event, ToolResultEvent):
            print(f"\n[← tool] {event.tool_name} → {event.result!r}")

        elif isinstance(event, DoneEvent):
            print(f"\n[done — {len(event.text)} chars total]")
            break


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    agent = await Agent.create(
        "poet",
        model=ModelConfig.from_env(),
    )

    await stream_with_loop(agent)
    print()
    await stream_with_events(agent)
    print()
    await stream_with_typed_events(agent)


if __name__ == "__main__":
    asyncio.run(main())
