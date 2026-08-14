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

from openjiuwen.sdk.core.config import ModelConfig, RemoteConfig
from openjiuwen.sdk.core.errors import (
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

from openjiuwen.sdk.core.agent import Agent, AgentResult

# ---------------------------------------------------------------------------
# Mode / channel constants
# ---------------------------------------------------------------------------

from openjiuwen.sdk.core.mode import AgentMode, ChannelId

# ---------------------------------------------------------------------------
# Stream events
# ---------------------------------------------------------------------------

from openjiuwen.sdk.core.stream import (
    DeltaEvent,
    DoneEvent,
    ErrorEvent,
    ReasoningEvent,
    StatusEvent,
    StreamEvent,
    TeamEvent,
    ToolCallEvent,
    ToolResultEvent,
    parse_gateway_envelope,
    parse_runtime_chunk,
)

# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

from openjiuwen.sdk.core.session import Message, Session

# ---------------------------------------------------------------------------
# Team
# ---------------------------------------------------------------------------

from openjiuwen.sdk.agents.team import Team, TeamResult

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

from openjiuwen.sdk.core.tools import SdkTool, ToolParam, tool

# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

from openjiuwen.sdk.core.events import EventEmitter

# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------

from openjiuwen.sdk.core.hooks import Hooks

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

from openjiuwen.sdk.agents.a2a import A2AError, A2AResult, RemoteAgent

# ---------------------------------------------------------------------------
# Memory
# ---------------------------------------------------------------------------

from openjiuwen.sdk.knowledge.memory import Memory, MemoryRecord, MemoryScope, make_memory

# ---------------------------------------------------------------------------
# Knowledge / RAG
# ---------------------------------------------------------------------------

from openjiuwen.sdk.knowledge import (
    AgenticRetriever,
    Document,
    GraphKnowledgeBase,
    KnowledgeBase,
    RetrievalResult,
    Retriever,
)

# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

from openjiuwen.sdk.optimize.eval import (
    EvalCase,
    EvalResult,
    Evaluator,
    ExactMatchMetric,
    HITTEvaluator,
    HITTResult,
    LLMAsJudgeMetric,
    Metric,
    MetricEvaluator,
)

# ---------------------------------------------------------------------------
# Tracing
# ---------------------------------------------------------------------------

from openjiuwen.sdk.observe.tracing import OtelTracer, OtelTracerConfig, get_tracer, init_otel_tracer

# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------

from openjiuwen.sdk.infra.workspace import Workspace, WorkspaceConfig

# ---------------------------------------------------------------------------
# Multimodal
# ---------------------------------------------------------------------------

from openjiuwen.sdk.multimodal import (
    Attachment,
    AudioInput,
    AudioModelConfig,
    ImageInput,
    MultimodalAgent,
    VisionModelConfig,
)

# ---------------------------------------------------------------------------
# Rollout
# ---------------------------------------------------------------------------

from openjiuwen.sdk.optimize.rollout import MultiRolloutConfig, MultiRolloutExecutor, RolloutResult

# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

from openjiuwen.sdk.control.permissions import PermissionEngine, PermissionLevel, PermissionRule

# ---------------------------------------------------------------------------
# Context Engine
# ---------------------------------------------------------------------------

from openjiuwen.sdk.control.context import ContextEngine, ContextEngineConfig, ContextStats

# ---------------------------------------------------------------------------
# LSP Integration
# ---------------------------------------------------------------------------

from openjiuwen.sdk.infra.lsp import (
    LSPCompletionItem,
    LSPDiagnostic,
    LSPIntegration,
    LSPPosition,
    LSPRange,
)

# ---------------------------------------------------------------------------
# Reinforcement Learning
# ---------------------------------------------------------------------------

from openjiuwen.sdk.optimize.rl import OfflineRL, OnlineRL, RLConfig, RLStepResult, RLTrajectory

# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

from openjiuwen.sdk.build.builder import (
    AgentBuilder,
    LlmAgentBuilder,
    PromptBuilder,
    WorkflowBuilder,
)

# ---------------------------------------------------------------------------
# Swarm
# ---------------------------------------------------------------------------

from openjiuwen.sdk.agents.swarm import SwarmFlow, SwarmResult

# ---------------------------------------------------------------------------
# MCP
# ---------------------------------------------------------------------------

from openjiuwen.sdk.infra.mcp import MCPServer

# ---------------------------------------------------------------------------
# Extended Workflow types
# ---------------------------------------------------------------------------

from openjiuwen.sdk.workflow import (
    End,
    LLMComponent,
    Start,
    SubWorkflowComponent,
    SubWorkflowNode,
)

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
    # Mode / channel
    "AgentMode",
    "ChannelId",
    # Stream events
    "StreamEvent",
    "DeltaEvent",
    "ReasoningEvent",
    "StatusEvent",
    "ToolCallEvent",
    "ToolResultEvent",
    "TeamEvent",
    "DoneEvent",
    "ErrorEvent",
    "parse_runtime_chunk",
    "parse_gateway_envelope",
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
    # Workflow (core)
    "Workflow",
    "WorkflowResult",
    "WorkflowNode",
    "LLMNode",
    "ToolNode",
    "ConditionNode",
    "WorkflowError",
    # Workflow (extended)
    "SubWorkflowNode",
    "SubWorkflowComponent",
    "LLMComponent",
    "Start",
    "End",
    # A2A
    "RemoteAgent",
    "A2AResult",
    "A2AError",
    # Memory
    "Memory",
    "MemoryRecord",
    "MemoryScope",
    "make_memory",
    # Knowledge / RAG
    "KnowledgeBase",
    "Document",
    "RetrievalResult",
    "Retriever",
    "AgenticRetriever",
    "GraphKnowledgeBase",
    # Evaluation
    "EvalCase",
    "EvalResult",
    "Metric",
    "ExactMatchMetric",
    "LLMAsJudgeMetric",
    "MetricEvaluator",
    "Evaluator",
    "HITTEvaluator",
    "HITTResult",
    # Tracing
    "OtelTracer",
    "OtelTracerConfig",
    "init_otel_tracer",
    "get_tracer",
    # Workspace
    "Workspace",
    "WorkspaceConfig",
    # Multimodal
    "MultimodalAgent",
    "ImageInput",
    "AudioInput",
    "VisionModelConfig",
    "AudioModelConfig",
    "Attachment",
    # Rollout
    "MultiRolloutConfig",
    "MultiRolloutExecutor",
    "RolloutResult",
    # Permissions
    "PermissionEngine",
    "PermissionLevel",
    "PermissionRule",
    # Context Engine
    "ContextEngine",
    "ContextEngineConfig",
    "ContextStats",
    # LSP
    "LSPIntegration",
    "LSPDiagnostic",
    "LSPCompletionItem",
    "LSPPosition",
    "LSPRange",
    # RL
    "OnlineRL",
    "OfflineRL",
    "RLConfig",
    "RLTrajectory",
    "RLStepResult",
    # Builder
    "AgentBuilder",
    "LlmAgentBuilder",
    "WorkflowBuilder",
    "PromptBuilder",
    # Swarm
    "SwarmFlow",
    "SwarmResult",
    # MCP
    "MCPServer",
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
