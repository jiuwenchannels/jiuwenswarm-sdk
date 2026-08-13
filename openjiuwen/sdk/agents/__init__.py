"""Multi-agent and collaborative primitives: Team, A2A, Swarm, SwarmFlow."""

from openjiuwen.sdk.agents.a2a import A2AError, A2AResult, RemoteAgent
from openjiuwen.sdk.agents.swarm import SwarmFlow, SwarmResult
from openjiuwen.sdk.agents.swarmflow import (
    ActivityRecord,
    PhaseRecord,
    SwarmFlowResult,
    agent,
    parallel,
    phase,
    pipeline,
    run_swarmflow,
)
from openjiuwen.sdk.agents.team import Team, TeamResult

__all__ = [
    "A2AError",
    "A2AResult",
    "ActivityRecord",
    "PhaseRecord",
    "RemoteAgent",
    "SwarmFlow",
    "SwarmFlowResult",
    "SwarmResult",
    "Team",
    "TeamResult",
    "agent",
    "parallel",
    "phase",
    "pipeline",
    "run_swarmflow",
]
