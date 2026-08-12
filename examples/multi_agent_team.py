"""multi_agent_team.py — coordinate multiple specialised agents as a team.

Shows:
  - Creating specialist agents
  - Assembling them into a Team
  - Using team.spawn() to distribute a high-level goal
  - Inspecting per-member outputs from TeamResult

Run:
    python examples/multi_agent_team.py
"""

import asyncio

from openjiuwen.sdk import Agent, ModelConfig, Team, tool


# ---------------------------------------------------------------------------
# Shared model config
# ---------------------------------------------------------------------------

MODEL = ModelConfig.from_env()


# ---------------------------------------------------------------------------
# Tools for individual agents
# ---------------------------------------------------------------------------

@tool
def search_web(query: str) -> str:
    """Search the web for up-to-date information (stub)."""
    return f"[stub] Top results for '{query}': result1, result2, result3"


@tool
def write_markdown(content: str, filename: str) -> str:
    """Write content to a markdown file (stub)."""
    return f"[stub] Wrote {len(content)} bytes to {filename}"


# ---------------------------------------------------------------------------
# Build specialist agents
# ---------------------------------------------------------------------------

async def build_agents() -> list[Agent]:
    researcher = await Agent.create(
        "researcher",
        model=MODEL,
        tools=[search_web],
        system_prompt="You are a research specialist. Gather factual information.",
    )

    writer = await Agent.create(
        "writer",
        model=MODEL,
        tools=[write_markdown],
        system_prompt="You are a technical writer. Turn research into clear prose.",
    )

    reviewer = await Agent.create(
        "reviewer",
        model=MODEL,
        system_prompt="You are a critical reviewer. Find gaps and suggest improvements.",
    )

    return [researcher, writer, reviewer]


# ---------------------------------------------------------------------------
# Assemble team and run
# ---------------------------------------------------------------------------

async def main() -> None:
    agents = await build_agents()
    team = await Team.create(agents, model=MODEL, team_name="report-team")

    print("Spawning team task…")
    result = await team.spawn(
        "Research the impact of transformer models on NLP, write a concise summary, "
        "and have it reviewed for completeness."
    )

    print("\nFinal output:")
    print(result.final_output[:800])
    print(f"\nSession: {result.session_id}")

    if result.member_outputs:
        print("\nPer-member outputs:")
        for member, output in result.member_outputs.items():
            print(f"  {member}: {output[:100]}…")


if __name__ == "__main__":
    asyncio.run(main())
