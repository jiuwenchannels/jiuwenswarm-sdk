"""32_team_stream.py — observe multi-agent team coordination in real time.

``team.spawn()`` waits for the full result.  ``team.stream()`` yields typed
:class:`~openjiuwen.sdk.StreamEvent` objects so you can watch each team
member start, produce output, and finish — as it happens.

Key events to watch for:
  * :class:`~openjiuwen.sdk.TeamEvent` ``type="team.agent_start"`` — a member began work
  * :class:`~openjiuwen.sdk.TeamEvent` ``type="team.handoff"``    — leader routed to a member
  * :class:`~openjiuwen.sdk.TeamEvent` ``type="team.agent_done"`` — a member finished
  * :class:`~openjiuwen.sdk.DeltaEvent`                           — text tokens (leader summary)
  * :class:`~openjiuwen.sdk.DoneEvent`                            — stream complete

Run:
    python examples/python/32_team_stream.py
"""

import asyncio

from openjiuwen.sdk import (
    Agent,
    AgentMode,
    DeltaEvent,
    DoneEvent,
    ErrorEvent,
    ModelConfig,
    StatusEvent,
    Team,
    TeamEvent,
    ToolCallEvent,
    ToolResultEvent,
    tool,
)


MODEL = ModelConfig.from_env()


# ---------------------------------------------------------------------------
# Stub tools for each specialist
# ---------------------------------------------------------------------------

@tool
def fetch_market_data(ticker: str) -> str:
    """Return latest price and volume for *ticker* (stub)."""
    return f"[stub] {ticker}: $182.34, vol 4.2 M"


@tool
def run_sentiment_analysis(headlines: str) -> str:
    """Score market sentiment from news headlines (stub)."""
    return "[stub] sentiment=0.63 (bullish)"


@tool
def generate_report(analysis: str, sentiment: str) -> str:
    """Combine analysis + sentiment into an investment report (stub)."""
    return f"[stub] Report generated: {len(analysis + sentiment)} chars"


# ---------------------------------------------------------------------------
# Build a three-agent team: analyst, sentiment, reporter
# ---------------------------------------------------------------------------

async def build_team() -> Team:
    analyst = await Agent.create(
        "analyst",
        model=MODEL,
        tools=[fetch_market_data],
        system_prompt=(
            "You are a market analyst. Fetch price data and produce a brief"
            " quantitative summary."
        ),
    )

    sentiment_agent = await Agent.create(
        "sentiment",
        model=MODEL,
        tools=[run_sentiment_analysis],
        system_prompt=(
            "You are a sentiment specialist. Analyse news headlines and score"
            " overall market mood."
        ),
    )

    reporter = await Agent.create(
        "reporter",
        model=MODEL,
        tools=[generate_report],
        system_prompt=(
            "You are a report writer. Combine quantitative data and sentiment"
            " scores into a concise investment brief."
        ),
    )

    return await Team.create(
        "investment-team",
        members=[analyst, sentiment_agent, reporter],
        model=MODEL,
        mode=AgentMode.TEAM,
    )


# ---------------------------------------------------------------------------
# Demo 1 — watch every event in real time
# ---------------------------------------------------------------------------

async def demo_live_events(team: Team) -> None:
    print("\n── Demo 1: live event stream ──────────────────────────────────────")

    goal = (
        "Produce an investment brief for AAPL: fetch latest data, score "
        "sentiment from recent headlines, then write the report."
    )

    agent_outputs: dict[str, list[str]] = {}

    async for event in team.stream(goal):

        if isinstance(event, TeamEvent):
            if event.type == "team.agent_start":
                print(f"\n\033[34m▶ [{event.agent_name}] started\033[0m")
                agent_outputs.setdefault(event.agent_name, [])

            elif event.type == "team.handoff":
                target = event.payload.get("target_agent", "?")
                print(f"\033[34m⇢ handoff → {target}\033[0m")

            elif event.type == "team.agent_done":
                out = event.payload.get("output", "")
                agent_outputs.setdefault(event.agent_name, []).append(out)
                print(f"\033[34m■ [{event.agent_name}] done\033[0m")

            elif event.type == "team.broadcast":
                print(f"\033[34m📢 broadcast: {event.payload.get('message', '')[:60]}\033[0m")

        elif isinstance(event, StatusEvent):
            marker = "✓" if event.is_complete else "…"
            print(f"\033[33m[status {marker}] {event.status}\033[0m")

        elif isinstance(event, ToolCallEvent):
            print(f"\033[36m  [tool→] {event.tool_name}({event.arguments})\033[0m")

        elif isinstance(event, ToolResultEvent):
            err = " ⚠" if event.is_error else ""
            print(f"\033[35m  [←tool]{err} {event.tool_name} → {event.result!r}\033[0m")

        elif isinstance(event, DeltaEvent):
            print(event.delta, end="", flush=True)

        elif isinstance(event, DoneEvent):
            print(f"\n\033[32m[done — {len(event.text)} chars]\033[0m")

        elif isinstance(event, ErrorEvent):
            print(f"\n\033[31m[error] {event.message}\033[0m")
            break

    if agent_outputs:
        print("\n── Per-member outputs ─────────────────────────────────────────────")
        for name, chunks in agent_outputs.items():
            snippet = " ".join(chunks)[:100]
            print(f"  {name}: {snippet!r}")


# ---------------------------------------------------------------------------
# Demo 2 — compare spawn() vs stream()
# ---------------------------------------------------------------------------

async def demo_spawn_vs_stream(team: Team) -> None:
    """Show that spawn() gives the same final answer; stream() adds visibility."""
    print("\n── Demo 2: spawn() vs stream() ────────────────────────────────────")

    # spawn(): blocking, returns TeamResult
    result = await team.spawn("What is the sentiment for TSLA right now?")
    print(f"spawn() → {result.final_output[:120]!r}")

    # stream(): same question, but we collect only the DeltaEvent text
    parts: list[str] = []
    async for event in team.stream("What is the sentiment for TSLA right now?"):
        if isinstance(event, DeltaEvent):
            parts.append(event.delta)
        elif isinstance(event, DoneEvent):
            break

    streamed = "".join(parts)
    print(f"stream() → {streamed[:120]!r}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    team = await build_team()
    await demo_live_events(team)
    await demo_spawn_vs_stream(team)


if __name__ == "__main__":
    asyncio.run(main())
