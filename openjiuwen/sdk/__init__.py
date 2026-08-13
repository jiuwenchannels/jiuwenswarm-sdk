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
# Memory
# ---------------------------------------------------------------------------

from openjiuwen.sdk.memory import Memory, MemoryRecord, MemoryScope, make_memory

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

from openjiuwen.sdk.eval import (
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

from openjiuwen.sdk.tracing import OtelTracer, OtelTracerConfig, get_tracer, init_otel_tracer

# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------

from openjiuwen.sdk.workspace import Workspace, WorkspaceConfig

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

from openjiuwen.sdk.rollout import MultiRolloutConfig, MultiRolloutExecutor, RolloutResult

# ---------------------------------------------------------------------------
# Permissions
# ---------------------------------------------------------------------------

from openjiuwen.sdk.permissions import PermissionEngine, PermissionLevel, PermissionRule

# ---------------------------------------------------------------------------
# Context Engine
# ---------------------------------------------------------------------------

from openjiuwen.sdk.context import ContextEngine, ContextEngineConfig, ContextStats

# ---------------------------------------------------------------------------
# LSP Integration
# ---------------------------------------------------------------------------

from openjiuwen.sdk.lsp import (
    LSPCompletionItem,
    LSPDiagnostic,
    LSPIntegration,
    LSPPosition,
    LSPRange,
)

# ---------------------------------------------------------------------------
# Reinforcement Learning
# ---------------------------------------------------------------------------

from openjiuwen.sdk.rl import OfflineRL, OnlineRL, RLConfig, RLStepResult, RLTrajectory

# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

from openjiuwen.sdk.builder import (
    AgentBuilder,
    LlmAgentBuilder,
    PromptBuilder,
    WorkflowBuilder,
)

# ---------------------------------------------------------------------------
# Swarm
# ---------------------------------------------------------------------------

from openjiuwen.sdk.swarm import SwarmFlow, SwarmResult

# ---------------------------------------------------------------------------
# MCP
# ---------------------------------------------------------------------------

from openjiuwen.sdk.mcp import MCPServer

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
