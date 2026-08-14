"""Typed streaming events.

When you call :meth:`~openjiuwen.sdk.core.agent.Agent.stream_events` or
:meth:`~openjiuwen.sdk.agents.team.Team.stream`, you receive a stream of
:class:`StreamEvent` subclasses instead of raw text tokens.

This lets you observe every phase of execution — reasoning, tool calls, team
coordination — not just the final text output.

Example::

    async for event in agent.stream_events("Explain async/await."):
        if isinstance(event, DeltaEvent):
            print(event.delta, end="", flush=True)
        elif isinstance(event, ReasoningEvent):
            print(f"[thinking] {event.delta}")
        elif isinstance(event, ToolCallEvent):
            print(f"\\n[tool] {event.tool_name}({event.arguments})")
        elif isinstance(event, DoneEvent):
            print()
            break

Event hierarchy
---------------
:class:`StreamEvent`
├── :class:`DeltaEvent`        — a text token from the model
├── :class:`ReasoningEvent`    — a token from the model's thinking phase
├── :class:`StatusEvent`       — processing status update
├── :class:`ToolCallEvent`     — tool is about to be called
├── :class:`ToolResultEvent`   — tool returned a result
├── :class:`TeamEvent`         — a multi-agent coordination event
├── :class:`DoneEvent`         — stream completed successfully
└── :class:`ErrorEvent`        — stream ended with an error
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


# ---------------------------------------------------------------------------
# Base
# ---------------------------------------------------------------------------


@dataclass
class StreamEvent:
    """Base class for all streaming events.

    Attributes:
        type: A string discriminator (e.g. ``"delta"``, ``"tool_call"``).
    """

    type: str


# ---------------------------------------------------------------------------
# Text output
# ---------------------------------------------------------------------------


@dataclass
class DeltaEvent(StreamEvent):
    """A text token or chunk produced by the model.

    This is the most common event.  Concatenating all ``delta`` values yields
    the complete agent response.

    Attributes:
        delta: The new text fragment.
    """

    type: Literal["delta"] = field(default="delta", init=False)
    delta: str = ""


# ---------------------------------------------------------------------------
# Reasoning / thinking
# ---------------------------------------------------------------------------


@dataclass
class ReasoningEvent(StreamEvent):
    """A token from the model's internal reasoning / thinking phase.

    Only emitted by models that support extended thinking (e.g. o3,
    Claude 3.7 with extended thinking).  Reasoning tokens are *not* part of
    the final response; they show the model's chain-of-thought.

    Attributes:
        delta: The new reasoning fragment.
    """

    type: Literal["reasoning"] = field(default="reasoning", init=False)
    delta: str = ""


# ---------------------------------------------------------------------------
# Processing status
# ---------------------------------------------------------------------------


@dataclass
class StatusEvent(StreamEvent):
    """A processing status update from the agent.

    Emitted while the agent is doing work that hasn't produced output yet —
    for example: *"Searching the web…"*, *"Running code…"*, *"Thinking…"*.

    Attributes:
        status:      Human-readable status message.
        is_complete: ``True`` when this status phase is finished.
    """

    type: Literal["status"] = field(default="status", init=False)
    status: str = ""
    is_complete: bool = False


# ---------------------------------------------------------------------------
# Tool interaction
# ---------------------------------------------------------------------------


@dataclass
class ToolCallEvent(StreamEvent):
    """The agent is about to invoke a tool.

    Attributes:
        tool_name:  Name of the tool being called.
        arguments:  Keyword arguments the agent is passing to the tool.
        call_id:    Opaque ID linking this event to the matching
                    :class:`ToolResultEvent`.
    """

    type: Literal["tool_call"] = field(default="tool_call", init=False)
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    call_id: str = ""


@dataclass
class ToolResultEvent(StreamEvent):
    """A tool has returned a result to the agent.

    Attributes:
        tool_name:  Name of the tool that was called.
        result:     The value returned by the tool.
        call_id:    Matches the :class:`ToolCallEvent` that triggered this.
        is_error:   ``True`` if the tool raised an exception.
    """

    type: Literal["tool_result"] = field(default="tool_result", init=False)
    tool_name: str = ""
    result: Any = None
    call_id: str = ""
    is_error: bool = False


# ---------------------------------------------------------------------------
# Team / swarm events
# ---------------------------------------------------------------------------


@dataclass
class TeamEvent(StreamEvent):
    """An event from a multi-agent team.

    Common ``type`` values:

    * ``"team.agent_start"``  — an agent in the team has been assigned work.
    * ``"team.agent_done"``   — an agent finished its subtask.
    * ``"team.handoff"``      — the leader is routing work to a teammate.
    * ``"team.broadcast"``    — a message is sent to all members.

    Attributes:
        agent_name: The team member this event relates to.
        payload:    Full event payload from the runtime.
    """

    type: str = "team"               # e.g. "team.agent_start"
    agent_name: str = ""
    payload: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Terminal events
# ---------------------------------------------------------------------------


@dataclass
class DoneEvent(StreamEvent):
    """The agent stream has completed successfully.

    Attributes:
        text: The complete assembled response (concatenation of all deltas).
    """

    type: Literal["done"] = field(default="done", init=False)
    text: str = ""


@dataclass
class ErrorEvent(StreamEvent):
    """The agent stream ended due to an error.

    Attributes:
        message: Human-readable error description.
    """

    type: Literal["error"] = field(default="error", init=False)
    message: str = ""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def parse_runtime_chunk(chunk: Any) -> StreamEvent:
    """Convert a raw runtime chunk into a typed :class:`StreamEvent`.

    Handles three chunk shapes emitted by the jiuwenswarm backend:

    * ``AgentResponseChunk`` objects with a ``.payload`` dict and
      ``event_type`` / ``type`` key.
    * Plain ``dict`` objects with an ``event_type`` or ``type`` key.
    * Plain ``str`` tokens (legacy / simple streaming).

    Args:
        chunk: A raw chunk from the runtime's async generator.

    Returns:
        A typed :class:`StreamEvent`.
    """
    # --- resolve payload and event_type ---
    if hasattr(chunk, "payload"):
        payload: dict[str, Any] = chunk.payload if isinstance(chunk.payload, dict) else {}
        event_type: str = (
            payload.get("event_type") or payload.get("type") or ""
        )
    elif isinstance(chunk, dict):
        payload = chunk
        event_type = chunk.get("event_type") or chunk.get("type") or ""
    else:
        # Plain string token — treat as delta
        return DeltaEvent(delta=str(chunk) if chunk else "")

    event_type = str(event_type)

    # --- map to typed events ---
    if event_type in ("chat.delta", "delta", "token"):
        delta = (
            payload.get("delta")
            or payload.get("content")
            or payload.get("text")
            or ""
        )
        return DeltaEvent(delta=str(delta))

    if event_type in ("chat.reasoning", "reasoning"):
        delta = (
            payload.get("content")
            or payload.get("delta")
            or payload.get("text")
            or ""
        )
        return ReasoningEvent(delta=str(delta))

    if event_type in ("chat.processing_status", "processing_status", "status"):
        return StatusEvent(
            status=str(payload.get("status", "")),
            is_complete=bool(payload.get("is_complete", payload.get("processing_complete", False))),
        )

    if event_type in ("chat.tool_call", "tool.call", "tool_call"):
        tc: Any = payload.get("tool_call") or payload
        if isinstance(tc, dict):
            return ToolCallEvent(
                tool_name=str(tc.get("name", "")),
                arguments=tc.get("arguments", {}),
                call_id=str(tc.get("id", tc.get("call_id", ""))),
            )
        return ToolCallEvent()

    if event_type in ("chat.tool_result", "tool.result", "tool_result"):
        return ToolResultEvent(
            tool_name=str(payload.get("tool_name", "")),
            result=payload.get("result") or payload.get("tool_result"),
            call_id=str(payload.get("call_id", "")),
            is_error=bool(payload.get("is_error", False)),
        )

    if event_type in ("chat.final", "final"):
        text = payload.get("content") or payload.get("text") or ""
        return DoneEvent(text=str(text))

    if event_type in ("chat.error", "error"):
        msg = payload.get("error") or payload.get("message") or str(chunk)
        return ErrorEvent(message=str(msg))

    if event_type.startswith("team."):
        return TeamEvent(
            type=event_type,
            agent_name=str(payload.get("agent_name", "")),
            payload=payload,
        )

    # Unknown — extract best-effort delta text
    text = (
        payload.get("delta")
        or payload.get("content")
        or payload.get("text")
        or ""
    )
    return DeltaEvent(delta=str(text))


def parse_gateway_envelope(env: dict[str, Any]) -> StreamEvent | None:
    """Convert a JiuwenSwarm gateway WebSocket envelope to a :class:`StreamEvent`.

    The gateway uses a simpler envelope format than the in-process runtime.
    Returns ``None`` for envelopes that should be silently skipped (e.g. ``ack``).

    Args:
        env: Parsed JSON envelope from the gateway.

    Returns:
        A typed event, or ``None`` if the envelope should be ignored.
    """
    t = env.get("type", "")

    if t == "token":
        return DeltaEvent(delta=str(env.get("text", env.get("delta", ""))))

    if t == "reasoning":
        return ReasoningEvent(delta=str(env.get("text", env.get("delta", ""))))

    if t == "status":
        return StatusEvent(
            status=str(env.get("status", env.get("message", ""))),
            is_complete=bool(env.get("is_complete", False)),
        )

    if t == "tool_call":
        return ToolCallEvent(
            tool_name=str(env.get("tool_name", env.get("name", ""))),
            arguments=env.get("arguments", {}),
            call_id=str(env.get("call_id", env.get("id", ""))),
        )

    if t == "tool_result":
        return ToolResultEvent(
            tool_name=str(env.get("tool_name", "")),
            result=env.get("result"),
            call_id=str(env.get("call_id", "")),
            is_error=bool(env.get("is_error", False)),
        )

    if t == "done":
        return DoneEvent(text=str(env.get("text", "")))

    if t == "error":
        return ErrorEvent(message=str(env.get("message", env.get("error", ""))))

    if t.startswith("team."):
        return TeamEvent(
            type=t,
            agent_name=str(env.get("agent_name", "")),
            payload=env,
        )

    # "ack", "sessions", "session_created" — caller handles these
    return None
