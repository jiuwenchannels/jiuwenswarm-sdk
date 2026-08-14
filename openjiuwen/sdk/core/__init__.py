"""Core agent primitives: Agent, config, errors, events, hooks, tools, session, stream."""

from openjiuwen.sdk.core.agent import Agent, AgentResult
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
from openjiuwen.sdk.core.events import EventEmitter
from openjiuwen.sdk.core.hooks import Hooks
from openjiuwen.sdk.core.session import Message, Session
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
from openjiuwen.sdk.core.mode import AgentMode, ChannelId
from openjiuwen.sdk.core.tools import SdkTool, tool

__all__ = [
    # Agent
    "Agent",
    "AgentResult",
    # Config
    "ModelConfig",
    "RemoteConfig",
    # Mode / channel constants
    "AgentMode",
    "ChannelId",
    # Errors
    "AgentError",
    "AuthError",
    "CheckpointError",
    "ConnectionError",
    "RuntimeNotAvailableError",
    "SdkError",
    "ServerError",
    "SessionError",
    "StreamError",
    "TeamError",
    "TimeoutError",
    "ToolError",
    # Events / hooks
    "EventEmitter",
    "Hooks",
    # Session
    "Message",
    "Session",
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
    # Tools
    "SdkTool",
    "tool",
]
