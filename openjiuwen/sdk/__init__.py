"""JiuwenSwarm Python SDK.

The SDK exposes a stable, versioned façade over the JiuwenSwarm runtime.
All public symbols are re-exported from this module — import from here, not
from sub-modules.

Quick start (in-process)::

    import asyncio
    from openjiuwen.sdk import Agent, ModelConfig

    async def main():
        agent = await Agent.create("my-agent", model=ModelConfig.from_env())
        result = await agent.run("What is the capital of France?")
        print(result.text)

    asyncio.run(main())

Quick start (remote)::

    from openjiuwen.sdk import Agent

    agent = await Agent.connect("ws://localhost:19000/v1/ws")
    result = await agent.run("Hello!")
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Version
# ---------------------------------------------------------------------------

__version__ = "0.1.0"

# ---------------------------------------------------------------------------
# Core types
# ---------------------------------------------------------------------------

from openjiuwen.sdk.config import ModelConfig, RemoteConfig
from openjiuwen.sdk.errors import (
    AgentError,
    AuthError,
    CheckpointError,
    ConnectionError,
    RuntimeNotAvailableError,
    SdkError,
    ServerError,
    SessionError,
    StreamError,
    TeamError,
    TimeoutError,
    ToolError,
)

# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

from openjiuwen.sdk.agent import Agent, AgentResult

# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

from openjiuwen.sdk.session import Message, Session

# ---------------------------------------------------------------------------
# Team
# ---------------------------------------------------------------------------

from openjiuwen.sdk.team import Team, TeamResult

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

from openjiuwen.sdk.tools import SdkTool, ToolParam, tool

# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

from openjiuwen.sdk.events import EventEmitter

# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------

from openjiuwen.sdk.hooks import Hooks

# ---------------------------------------------------------------------------
# Workflow
# ---------------------------------------------------------------------------

from openjiuwen.sdk.workflow import (
    ConditionNode,
    LLMNode,
    ToolNode,
    Workflow,
    WorkflowError,
    WorkflowNode,
    WorkflowResult,
)

# ---------------------------------------------------------------------------
# A2A (agent-to-agent)
# ---------------------------------------------------------------------------

from openjiuwen.sdk.a2a import A2AError, A2AResult, RemoteAgent

# ---------------------------------------------------------------------------
# Public surface
# ---------------------------------------------------------------------------

__all__ = [
    # Version
    "__version__",
    # Config
    "ModelConfig",
    "RemoteConfig",
    # Agent
    "Agent",
    "AgentResult",
    # Session
    "Session",
    "Message",
    # Team
    "Team",
    "TeamResult",
    # Tools
    "tool",
    "SdkTool",
    "ToolParam",
    # Events
    "EventEmitter",
    # Hooks
    "Hooks",
    # Workflow
    "Workflow",
    "WorkflowResult",
    "WorkflowNode",
    "LLMNode",
    "ToolNode",
    "ConditionNode",
    "WorkflowError",
    # A2A
    "RemoteAgent",
    "A2AResult",
    "A2AError",
    # Errors
    "SdkError",
    "RuntimeNotAvailableError",
    "ConnectionError",
    "AuthError",
    "SessionError",
    "AgentError",
    "ToolError",
    "CheckpointError",
    "TeamError",
    "StreamError",
    "TimeoutError",
    "ServerError",
]
