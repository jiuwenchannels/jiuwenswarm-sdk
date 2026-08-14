"""31_stream_events.py — typed streaming events.

Instead of raw text tokens, ``stream_events()`` yields strongly-typed
:class:`~openjiuwen.sdk.StreamEvent` subclasses so you can react to every
phase of agent execution: reasoning, tool calls, status updates, and errors —
not just the final text output.

This example also shows:
  * ``AgentMode`` constants instead of bare strings
  * ``ChannelId`` constants for channel routing
  * ``context_prefix`` to prepend notebook / IDE state to a prompt
  * Cancellation mid-stream via ``gen.aclose()``

Run:
    python examples/python/31_stream_events.py
"""

import asyncio

from openjiuwen.sdk import (
    Agent,
    AgentMode,
    ChannelId,
    DeltaEvent,
    DoneEvent,
    ErrorEvent,
    ModelConfig,
    ReasoningEvent,
    StatusEvent,
    TeamEvent,
    ToolCallEvent,
    ToolResultEvent,
    tool,
)


# ---------------------------------------------------------------------------
# A toy tool so we can see ToolCallEvent / ToolResultEvent in action
# ---------------------------------------------------------------------------

@tool
def word_count(text: str) -> int:
    """Count words in *text*."""
    return len(text.split())


# ---------------------------------------------------------------------------
# Style 1 — rich event-by-event display
# ---------------------------------------------------------------------------

async def demo_all_events(agent: Agent) -> None:
    """Print every event type with a coloured prefix."""
    print("\n── Style 1: all event types ───────────────────────────────────────")

    prompt = "Count the words in 'the quick brown fox' then summarise what you did."

    async for event in agent.stream_events(prompt):
        if isinstance(event, DeltaEvent):
            print(event.delta, end="", flush=True)

        elif isinstance(event, ReasoningEvent):
            # Models with extended thinking emit these before answering
            print(f"\033[2m[thinking] {event.delta}\033[0m", end="", flush=True)

        elif isinstance(event, StatusEvent):
            marker = "✓" if event.is_complete else "…"
            print(f"\n\033[33m[status {marker}] {event.status}\033[0m")

        elif isinstance(event, ToolCallEvent):
            print(f"\n\033[36m[tool→] {event.tool_name}({event.arguments})  id={event.call_id}\033[0m")

        elif isinstance(event, ToolResultEvent):
            err = " ⚠ error" if event.is_error else ""
            print(f"\n\033[35m[←tool]{err} {event.tool_name} → {event.result!r}  id={event.call_id}\033[0m")

        elif isinstance(event, TeamEvent):
            print(f"\n\033[34m[team/{event.type}] agent={event.agent_name}\033[0m")

        elif isinstance(event, DoneEvent):
            print(f"\n\033[32m[done — {len(event.text)} chars]\033[0m")

        elif isinstance(event, ErrorEvent):
            print(f"\n\033[31m[error] {event.message}\033[0m")
            break


# ---------------------------------------------------------------------------
# Style 2 — collect only the text, discard metadata events
# ---------------------------------------------------------------------------

async def demo_text_only(agent: Agent) -> None:
    """Silently discard non-text events and print only the response."""
    print("\n── Style 2: text only ─────────────────────────────────────────────")

    parts: list[str] = []
    async for event in agent.stream_events("What is 7 × 8?"):
        if isinstance(event, DeltaEvent):
            parts.append(event.delta)
        elif isinstance(event, DoneEvent):
            break

    print("".join(parts))


# ---------------------------------------------------------------------------
# Style 3 — context_prefix (simulate injecting file context from an IDE)
# ---------------------------------------------------------------------------

async def demo_context_prefix(agent: Agent) -> None:
    """Prepend file context before the user's question."""
    print("\n── Style 3: context_prefix ────────────────────────────────────────")

    file_context = """\
# Current file: src/utils.py
def add(a: int, b: int) -> int:
    return a + b"""

    user_question = "Is there a bug in this function?"

    async for event in agent.stream_events(
        user_question,
        context_prefix=file_context,
    ):
        if isinstance(event, DeltaEvent):
            print(event.delta, end="", flush=True)
        elif isinstance(event, DoneEvent):
            print()
            break


# ---------------------------------------------------------------------------
# Style 4 — early cancellation
# ---------------------------------------------------------------------------

async def demo_cancel(agent: Agent) -> None:
    """Cancel the stream after receiving the first few tokens."""
    print("\n── Style 4: cancellation ──────────────────────────────────────────")

    gen = agent.stream_events("Recite the entire alphabet, one letter per line.")

    tokens_seen = 0
    async for event in gen:
        if isinstance(event, DeltaEvent):
            print(event.delta, end="", flush=True)
            tokens_seen += 1
            if tokens_seen >= 5:
                print("\n[cancelled after 5 tokens]")
                await gen.aclose()
                break
        elif isinstance(event, DoneEvent):
            break


# ---------------------------------------------------------------------------
# Style 5 — AgentMode + ChannelId constants
# ---------------------------------------------------------------------------

async def demo_mode_and_channel(agent: Agent) -> None:
    """Use AgentMode and ChannelId constants instead of bare strings."""
    print("\n── Style 5: AgentMode / ChannelId ─────────────────────────────────")

    # In-process mode ignores channel_id, but the same code works against a
    # remote gateway where channel_id routes to the correct pipeline.
    async for event in agent.stream_events(
        "Write a function that checks if a number is prime.",
        mode=AgentMode.CODE,
        channel_id=ChannelId.API,
    ):
        if isinstance(event, DeltaEvent):
            print(event.delta, end="", flush=True)
        elif isinstance(event, DoneEvent):
            print()
            break


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    agent = await Agent.create(
        "demo",
        model=ModelConfig.from_env(),
        tools=[word_count],
        # Set defaults — overridable per-call
        mode=AgentMode.AGENT,
        channel_id=ChannelId.API,
    )

    await demo_all_events(agent)
    await demo_text_only(agent)
    await demo_context_prefix(agent)
    await demo_cancel(agent)
    await demo_mode_and_channel(agent)


if __name__ == "__main__":
    asyncio.run(main())
