"""24_hitt.py — human-in-the-team (HITT) for collaborative human-AI teams.

Corresponds to §24 of the usage examples.

Shows:
  - TeamMemberSpec with TeamRole.HUMAN_AGENT adding a real person to the team
  - TeamAgentSpec with enable_hitt=True activating the HITT protocol
  - Team.create(spec=spec) for structured team construction
  - The team pauses at decision checkpoints and routes messages to the human
  - Human interacts via the active session WebSocket

Run:
    python examples/24_hitt.py

Note:
    The human agent receives messages through the configured transport
    (WebSocket session, stdin, etc.) and can reply, approve, or redirect.
"""

import asyncio
from openjiuwen.sdk import Agent, Team, ModelConfig
from openjiuwen.agent_teams.schema.team import TeamRole, TeamMemberSpec, TeamAgentSpec


async def main():
    model_cfg = ModelConfig.from_env()

    # Two AI agents
    researcher = await Agent.create("researcher", model=model_cfg)
    writer     = await Agent.create("writer",     model=model_cfg)

    # Specify the team structure including a human member
    spec = TeamAgentSpec(
        predefined_members=[
            TeamMemberSpec(
                member_name="researcher",
                role_type=TeamRole.TEAMMATE,
                agent=researcher,
            ),
            TeamMemberSpec(
                member_name="writer",
                role_type=TeamRole.TEAMMATE,
                agent=writer,
            ),
            TeamMemberSpec(
                member_name="alice",
                role_type=TeamRole.HUMAN_AGENT,  # human participant
                description="Domain expert who approves research plans.",
            ),
        ],
        enable_hitt=True,   # activate human-in-the-team protocol
    )

    team = await Team.create(spec=spec, model=model_cfg)

    # The team will pause and route messages to the human member at decision points.
    # The human interacts via the configured transport (WebSocket session, stdin, etc.)
    result = await team.spawn(
        "Research the impact of LLMs on legal discovery workflows and write a report."
    )
    print(result.final_output)


if __name__ == "__main__":
    asyncio.run(main())
