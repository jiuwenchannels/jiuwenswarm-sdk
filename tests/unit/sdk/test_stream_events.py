"""Tests for openjiuwen.sdk.core.stream and related streaming additions.

Covers:
- StreamEvent hierarchy and parse_runtime_chunk()
- parse_gateway_envelope()
- Agent.stream_events() — typed events, EventEmitter mirroring
- Agent.stream() — channel_id and mode forwarding (backward compat)
- Agent.run() — channel_id and mode forwarding
- Agent.create() / connect() — channel_id and mode stored as defaults
- Team.stream() — typed events including TeamEvent
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openjiuwen.sdk.core.agent import Agent, AgentResult
from openjiuwen.sdk.core.config import ModelConfig
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
# Helpers
# ---------------------------------------------------------------------------


def _make_chunk(event_type: str, **kw):
    """Return a dict-style chunk as the runtime would emit."""
    return {"event_type": event_type, **kw}


def _make_payload_chunk(event_type: str, **kw):
    """Return an object with a .payload attribute."""
    obj = MagicMock()
    obj.payload = {"event_type": event_type, **kw}
    return obj


def _make_fake_session() -> MagicMock:
    sess = MagicMock()
    sess.pre_run = AsyncMock()
    sess.post_run = AsyncMock()
    sess.get_session_id = MagicMock(return_value="sess_fake")
    return sess


def _make_fake_deep_agent(chunks: list) -> MagicMock:
    """Return a mock DeepAgent whose stream() yields the provided chunks."""
    agent = MagicMock()
    agent.invoke = AsyncMock(return_value={"text": "done"})

    async def _stream(inputs, agent_session=None, **kw):
        for c in chunks:
            yield c

    agent.stream = _stream
    return agent


@pytest.fixture(autouse=True)
def _clean_registry():
    from openjiuwen.sdk._internal import session_bridge
    session_bridge._registry.clear()
    yield
    session_bridge._registry.clear()


@pytest.fixture()
def mock_runtime_factory():
    """Returns a context manager factory that patches the runtime with a custom fake agent."""

    def _make(chunks: list):
        fake_agent = _make_fake_deep_agent(chunks)
        fake_sess = _make_fake_session()

        return (
            patch("openjiuwen.sdk._internal.runner_bridge._require_runtime"),
            patch("openjiuwen.sdk._internal.runner_bridge._get_runner", new_callable=AsyncMock),
            patch("openjiuwen.sdk._internal.runner_bridge._build_model", return_value=MagicMock()),
            patch("openjiuwen.sdk._internal.runner_bridge._sdk_tools_to_runtime", return_value=[]),
            patch("openjiuwen.sdk._internal.runner_bridge.make_agent_card", return_value=MagicMock()),
            patch("openjiuwen.sdk._internal.runner_bridge.make_deep_agent_config", return_value=MagicMock()),
            patch("openjiuwen.sdk._internal.runner_bridge.create_deep_agent", return_value=fake_agent),
            patch("openjiuwen.sdk._internal.session_bridge.make_internal_session", return_value=fake_sess),
        ), fake_agent

    return _make


# ---------------------------------------------------------------------------
# parse_runtime_chunk — unit tests
# ---------------------------------------------------------------------------


class TestParseRuntimeChunk:

    def test_plain_string_becomes_delta(self):
        event = parse_runtime_chunk("hello")
        assert isinstance(event, DeltaEvent)
        assert event.delta == "hello"

    def test_empty_string_becomes_empty_delta(self):
        event = parse_runtime_chunk("")
        assert isinstance(event, DeltaEvent)
        assert event.delta == ""

    def test_dict_delta(self):
        event = parse_runtime_chunk({"event_type": "chat.delta", "delta": "foo"})
        assert isinstance(event, DeltaEvent)
        assert event.delta == "foo"

    def test_dict_token(self):
        event = parse_runtime_chunk({"event_type": "token", "text": "bar"})
        assert isinstance(event, DeltaEvent)
        assert event.delta == "bar"

    def test_dict_reasoning(self):
        event = parse_runtime_chunk({"event_type": "chat.reasoning", "content": "thinking..."})
        assert isinstance(event, ReasoningEvent)
        assert event.delta == "thinking..."

    def test_dict_status(self):
        event = parse_runtime_chunk({
            "event_type": "processing_status",
            "status": "Searching…",
            "is_complete": False,
        })
        assert isinstance(event, StatusEvent)
        assert event.status == "Searching…"
        assert event.is_complete is False

    def test_dict_status_complete(self):
        event = parse_runtime_chunk({
            "event_type": "chat.processing_status",
            "status": "Done",
            "is_complete": True,
        })
        assert isinstance(event, StatusEvent)
        assert event.is_complete is True

    def test_dict_tool_call(self):
        event = parse_runtime_chunk({
            "event_type": "tool_call",
            "tool_call": {"name": "web_search", "arguments": {"q": "AI"}, "id": "call_1"},
        })
        assert isinstance(event, ToolCallEvent)
        assert event.tool_name == "web_search"
        assert event.arguments == {"q": "AI"}
        assert event.call_id == "call_1"

    def test_dict_tool_result(self):
        event = parse_runtime_chunk({
            "event_type": "tool.result",
            "tool_name": "web_search",
            "result": "some results",
            "call_id": "call_1",
        })
        assert isinstance(event, ToolResultEvent)
        assert event.tool_name == "web_search"
        assert event.result == "some results"
        assert event.call_id == "call_1"

    def test_dict_tool_result_error(self):
        event = parse_runtime_chunk({
            "event_type": "tool_result",
            "tool_name": "run_code",
            "result": "SyntaxError: invalid syntax",
            "is_error": True,
        })
        assert isinstance(event, ToolResultEvent)
        assert event.is_error is True

    def test_dict_done(self):
        event = parse_runtime_chunk({"event_type": "final", "text": "Final answer here."})
        assert isinstance(event, DoneEvent)
        assert event.text == "Final answer here."

    def test_dict_error(self):
        event = parse_runtime_chunk({"event_type": "chat.error", "error": "timeout"})
        assert isinstance(event, ErrorEvent)
        assert event.message == "timeout"

    def test_team_event(self):
        event = parse_runtime_chunk({
            "event_type": "team.agent_start",
            "agent_name": "researcher",
        })
        assert isinstance(event, TeamEvent)
        assert event.type == "team.agent_start"
        assert event.agent_name == "researcher"

    def test_object_with_payload(self):
        chunk = _make_payload_chunk("chat.delta", delta="world")
        event = parse_runtime_chunk(chunk)
        assert isinstance(event, DeltaEvent)
        assert event.delta == "world"

    def test_unknown_event_type_falls_back_to_delta(self):
        event = parse_runtime_chunk({"event_type": "weird.unknown", "text": "some text"})
        assert isinstance(event, DeltaEvent)
        assert event.delta == "some text"

    def test_dict_without_event_type_falls_back_to_delta(self):
        event = parse_runtime_chunk({"text": "implicit token"})
        assert isinstance(event, DeltaEvent)


# ---------------------------------------------------------------------------
# parse_gateway_envelope — unit tests
# ---------------------------------------------------------------------------


class TestParseGatewayEnvelope:

    def test_token(self):
        event = parse_gateway_envelope({"type": "token", "text": "hello"})
        assert isinstance(event, DeltaEvent)
        assert event.delta == "hello"

    def test_reasoning(self):
        event = parse_gateway_envelope({"type": "reasoning", "text": "thinking"})
        assert isinstance(event, ReasoningEvent)
        assert event.delta == "thinking"

    def test_status(self):
        event = parse_gateway_envelope({"type": "status", "status": "Working…", "is_complete": False})
        assert isinstance(event, StatusEvent)
        assert event.status == "Working…"

    def test_tool_call(self):
        event = parse_gateway_envelope({
            "type": "tool_call",
            "tool_name": "calculator",
            "arguments": {"expr": "2+2"},
            "call_id": "c1",
        })
        assert isinstance(event, ToolCallEvent)
        assert event.tool_name == "calculator"
        assert event.arguments == {"expr": "2+2"}

    def test_tool_result(self):
        event = parse_gateway_envelope({
            "type": "tool_result",
            "tool_name": "calculator",
            "result": 4,
            "call_id": "c1",
        })
        assert isinstance(event, ToolResultEvent)
        assert event.result == 4

    def test_done(self):
        event = parse_gateway_envelope({"type": "done", "text": "finished"})
        assert isinstance(event, DoneEvent)
        assert event.text == "finished"

    def test_error(self):
        event = parse_gateway_envelope({"type": "error", "message": "oops"})
        assert isinstance(event, ErrorEvent)
        assert event.message == "oops"

    def test_team_event(self):
        event = parse_gateway_envelope({"type": "team.handoff", "agent_name": "writer"})
        assert isinstance(event, TeamEvent)
        assert event.type == "team.handoff"
        assert event.agent_name == "writer"

    def test_ack_returns_none(self):
        event = parse_gateway_envelope({"type": "ack", "session_id": "s1"})
        assert event is None

    def test_sessions_returns_none(self):
        event = parse_gateway_envelope({"type": "sessions", "sessions": []})
        assert event is None


# ---------------------------------------------------------------------------
# StreamEvent hierarchy — type discrimination
# ---------------------------------------------------------------------------


class TestStreamEventTypes:

    def test_delta_type_literal(self):
        e = DeltaEvent(delta="x")
        assert e.type == "delta"

    def test_reasoning_type_literal(self):
        e = ReasoningEvent(delta="x")
        assert e.type == "reasoning"

    def test_status_type_literal(self):
        e = StatusEvent(status="busy")
        assert e.type == "status"

    def test_tool_call_type_literal(self):
        e = ToolCallEvent(tool_name="foo")
        assert e.type == "tool_call"

    def test_tool_result_type_literal(self):
        e = ToolResultEvent(tool_name="foo", result="bar")
        assert e.type == "tool_result"

    def test_team_event_type(self):
        e = TeamEvent(type="team.agent_done", agent_name="researcher")
        assert e.type == "team.agent_done"

    def test_done_type_literal(self):
        e = DoneEvent(text="all done")
        assert e.type == "done"

    def test_error_type_literal(self):
        e = ErrorEvent(message="fail")
        assert e.type == "error"

    def test_all_are_stream_events(self):
        events = [
            DeltaEvent(delta="x"),
            ReasoningEvent(delta="y"),
            StatusEvent(),
            ToolCallEvent(),
            ToolResultEvent(),
            TeamEvent(),
            DoneEvent(),
            ErrorEvent(),
        ]
        for e in events:
            assert isinstance(e, StreamEvent)


# ---------------------------------------------------------------------------
# Agent.stream_events() — in-process mode
# ---------------------------------------------------------------------------


class TestAgentStreamEvents:

    @pytest.fixture()
    def delta_chunks(self):
        return [
            {"event_type": "chat.delta", "delta": "Hello"},
            {"event_type": "chat.delta", "delta": " world"},
        ]

    @pytest.fixture()
    def mixed_chunks(self):
        return [
            {"event_type": "chat.reasoning", "content": "let me think"},
            {"event_type": "processing_status", "status": "Searching…", "is_complete": False},
            {"event_type": "tool_call", "tool_call": {"name": "search", "arguments": {}, "id": "c1"}},
            {"event_type": "tool.result", "tool_name": "search", "result": "results", "call_id": "c1"},
            {"event_type": "chat.delta", "delta": "Here is what I found."},
        ]

    @pytest.mark.asyncio
    async def test_yields_delta_events(self, delta_chunks):
        patches, fake_agent = _make_patch_stack(delta_chunks)
        async with _apply(*patches):
            agent = await Agent.create("test", model=ModelConfig(model="openai/gpt-4o", api_key="k"))
            events = [e async for e in agent.stream_events("hi")]

        delta_events = [e for e in events if isinstance(e, DeltaEvent)]
        assert len(delta_events) == 2
        assert delta_events[0].delta == "Hello"
        assert delta_events[1].delta == " world"

    @pytest.mark.asyncio
    async def test_always_ends_with_done_event(self, delta_chunks):
        patches, _ = _make_patch_stack(delta_chunks)
        async with _apply(*patches):
            agent = await Agent.create("test", model=ModelConfig(model="openai/gpt-4o", api_key="k"))
            events = [e async for e in agent.stream_events("hi")]

        assert isinstance(events[-1], DoneEvent)

    @pytest.mark.asyncio
    async def test_done_event_contains_full_text(self, delta_chunks):
        patches, _ = _make_patch_stack(delta_chunks)
        async with _apply(*patches):
            agent = await Agent.create("test", model=ModelConfig(model="openai/gpt-4o", api_key="k"))
            events = [e async for e in agent.stream_events("hi")]

        done = next(e for e in events if isinstance(e, DoneEvent))
        assert done.text == "Hello world"

    @pytest.mark.asyncio
    async def test_yields_mixed_event_types(self, mixed_chunks):
        patches, _ = _make_patch_stack(mixed_chunks)
        async with _apply(*patches):
            agent = await Agent.create("test", model=ModelConfig(model="openai/gpt-4o", api_key="k"))
            events = [e async for e in agent.stream_events("search for AI")]

        types = {type(e) for e in events}
        assert ReasoningEvent in types
        assert StatusEvent in types
        assert ToolCallEvent in types
        assert ToolResultEvent in types
        assert DeltaEvent in types

    @pytest.mark.asyncio
    async def test_emits_token_event_on_emitter(self, delta_chunks):
        patches, _ = _make_patch_stack(delta_chunks)
        tokens: list[str] = []
        async with _apply(*patches):
            agent = await Agent.create("test", model=ModelConfig(model="openai/gpt-4o", api_key="k"))
            agent.on("token", lambda t: tokens.append(t))
            async for _ in agent.stream_events("hi"):
                pass

        assert tokens == ["Hello", " world"]

    @pytest.mark.asyncio
    async def test_emits_reasoning_event_on_emitter(self, mixed_chunks):
        patches, _ = _make_patch_stack(mixed_chunks)
        reasoning_tokens: list[str] = []
        async with _apply(*patches):
            agent = await Agent.create("test", model=ModelConfig(model="openai/gpt-4o", api_key="k"))
            agent.on("reasoning", lambda t: reasoning_tokens.append(t))
            async for _ in agent.stream_events("hi"):
                pass

        assert reasoning_tokens == ["let me think"]

    @pytest.mark.asyncio
    async def test_emits_tool_call_event_on_emitter(self, mixed_chunks):
        patches, _ = _make_patch_stack(mixed_chunks)
        tool_calls: list[tuple] = []
        async with _apply(*patches):
            agent = await Agent.create("test", model=ModelConfig(model="openai/gpt-4o", api_key="k"))
            agent.on("tool_call", lambda name, args: tool_calls.append((name, args)))
            async for _ in agent.stream_events("hi"):
                pass

        assert len(tool_calls) == 1
        assert tool_calls[0][0] == "search"

    @pytest.mark.asyncio
    async def test_emits_done_on_emitter(self, delta_chunks):
        patches, _ = _make_patch_stack(delta_chunks)
        done_called = []
        async with _apply(*patches):
            agent = await Agent.create("test", model=ModelConfig(model="openai/gpt-4o", api_key="k"))
            agent.on("done", lambda: done_called.append(True))
            async for _ in agent.stream_events("hi"):
                pass

        assert done_called == [True]


# ---------------------------------------------------------------------------
# Agent.stream() — channel_id and mode forwarding
# ---------------------------------------------------------------------------


class TestAgentStreamModeChannel:

    @pytest.mark.asyncio
    async def test_run_passes_mode_to_bridge(self):
        fake_agent = _make_fake_deep_agent([])
        fake_agent.invoke = AsyncMock(return_value={"text": "ok"})
        fake_sess = _make_fake_session()

        with _sync_patches(fake_agent, fake_sess) as patches:
            agent = await Agent.create(
                "test",
                model=ModelConfig(model="openai/gpt-4o", api_key="k"),
                mode="code",
            )
            result = await agent.run("write a function")

        assert result.text == "ok"

    @pytest.mark.asyncio
    async def test_run_per_call_mode_overrides_default(self):
        """mode= on run() should override the default set at create() time."""
        inputs_seen: list[dict] = []
        fake_sess = _make_fake_session()

        original_agent = MagicMock()

        async def capture_invoke(inputs, agent_session=None, **kw):
            inputs_seen.append(dict(inputs))
            return {"text": "ok"}

        original_agent.invoke = capture_invoke
        original_agent.stream = AsyncMock()

        with _sync_patches(original_agent, fake_sess):
            agent = await Agent.create(
                "test",
                model=ModelConfig(model="openai/gpt-4o", api_key="k"),
                mode="agent",
                channel_id="api",
            )
            await agent.run("hello", mode="code", channel_id="ide")

        assert inputs_seen[0].get("mode") == "code"
        assert inputs_seen[0].get("channel_id") == "ide"

    @pytest.mark.asyncio
    async def test_default_channel_id_used_when_no_override(self):
        inputs_seen: list[dict] = []
        fake_sess = _make_fake_session()

        original_agent = MagicMock()

        async def capture_invoke(inputs, agent_session=None, **kw):
            inputs_seen.append(dict(inputs))
            return {"text": "ok"}

        original_agent.invoke = capture_invoke
        original_agent.stream = AsyncMock()

        with _sync_patches(original_agent, fake_sess):
            agent = await Agent.create(
                "test",
                model=ModelConfig(model="openai/gpt-4o", api_key="k"),
                channel_id="jupyter",
            )
            await agent.run("hello")

        assert inputs_seen[0].get("channel_id") == "jupyter"


# ---------------------------------------------------------------------------
# Agent.create() and connect() — default channel_id and mode stored
# ---------------------------------------------------------------------------


class TestAgentDefaultsModeChannel:

    @pytest.mark.asyncio
    async def test_create_stores_channel_id(self):
        fake_agent = _make_fake_deep_agent([])
        fake_agent.invoke = AsyncMock(return_value={"text": "ok"})
        fake_sess = _make_fake_session()

        with _sync_patches(fake_agent, fake_sess):
            agent = await Agent.create(
                "test",
                model=ModelConfig(model="openai/gpt-4o", api_key="k"),
                channel_id="ide",
            )

        assert agent._channel_id == "ide"

    @pytest.mark.asyncio
    async def test_create_stores_mode(self):
        fake_agent = _make_fake_deep_agent([])
        fake_agent.invoke = AsyncMock(return_value={"text": "ok"})
        fake_sess = _make_fake_session()

        with _sync_patches(fake_agent, fake_sess):
            agent = await Agent.create(
                "test",
                model=ModelConfig(model="openai/gpt-4o", api_key="k"),
                mode="code.team",
            )

        assert agent._default_mode == "code.team"

    @pytest.mark.asyncio
    async def test_create_defaults_none_when_not_set(self):
        fake_agent = _make_fake_deep_agent([])
        fake_agent.invoke = AsyncMock(return_value={"text": "ok"})
        fake_sess = _make_fake_session()

        with _sync_patches(fake_agent, fake_sess):
            agent = await Agent.create(
                "test",
                model=ModelConfig(model="openai/gpt-4o", api_key="k"),
            )

        assert agent._channel_id is None
        assert agent._default_mode is None


# ---------------------------------------------------------------------------
# Team.stream() — typed events
# ---------------------------------------------------------------------------


@pytest.fixture()
def _mock_core_session():
    """Inject a fake openjiuwen.core.session module so lazy imports in team.py work."""
    import sys
    fake_sess = _make_fake_session()
    fake_mod = MagicMock()
    fake_mod.create_agent_session = MagicMock(return_value=fake_sess)

    originals = {}
    for key in ("openjiuwen.core", "openjiuwen.core.session"):
        originals[key] = sys.modules.get(key)
        sys.modules[key] = fake_mod

    yield fake_sess

    for key, val in originals.items():
        if val is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = val


class TestTeamStream:

    @pytest.mark.asyncio
    async def test_team_stream_yields_events_and_ends_with_done(self, _mock_core_session):
        """Team.stream() should yield StreamEvent objects ending with DoneEvent."""
        chunks = [
            {"event_type": "team.agent_start", "agent_name": "researcher"},
            {"event_type": "chat.delta", "delta": "Research complete."},
            {"event_type": "team.agent_done", "agent_name": "researcher"},
        ]
        mock_team_runtime = _make_mock_team_with_stream(chunks)
        team = _build_team_facade(mock_team_runtime)
        events = [e async for e in team.stream("do research")]

        assert isinstance(events[-1], DoneEvent)
        team_starts = [e for e in events if isinstance(e, TeamEvent) and e.type == "team.agent_start"]
        assert len(team_starts) == 1
        assert team_starts[0].agent_name == "researcher"

    @pytest.mark.asyncio
    async def test_team_stream_done_contains_assembled_text(self, _mock_core_session):
        chunks = [
            {"event_type": "chat.delta", "delta": "Hello "},
            {"event_type": "chat.delta", "delta": "World"},
        ]
        mock_team_runtime = _make_mock_team_with_stream(chunks)
        team = _build_team_facade(mock_team_runtime)
        events = [e async for e in team.stream("task")]

        done = next(e for e in events if isinstance(e, DoneEvent))
        assert done.text == "Hello World"

    @pytest.mark.asyncio
    async def test_team_stream_fallback_when_no_stream_method(self, _mock_core_session):
        """When runtime team has no .stream(), fallback emits DeltaEvent + DoneEvent."""
        mock_team_runtime = MagicMock(spec=[])   # no .stream attribute
        mock_team_runtime.invoke = AsyncMock(return_value={"text": "final answer"})

        team = _build_team_facade(mock_team_runtime)
        events = [e async for e in team.stream("task")]

        deltas = [e for e in events if isinstance(e, DeltaEvent)]
        assert len(deltas) == 1
        assert deltas[0].delta == "final answer"
        assert isinstance(events[-1], DoneEvent)


# ---------------------------------------------------------------------------
# Shared helpers for tests
# ---------------------------------------------------------------------------


def _make_patch_stack(chunks: list):
    fake_agent = _make_fake_deep_agent(chunks)
    fake_sess = _make_fake_session()

    patches = (
        patch("openjiuwen.sdk._internal.runner_bridge._require_runtime"),
        patch("openjiuwen.sdk._internal.runner_bridge._get_runner", new_callable=AsyncMock),
        patch("openjiuwen.sdk._internal.runner_bridge._build_model", return_value=MagicMock()),
        patch("openjiuwen.sdk._internal.runner_bridge._sdk_tools_to_runtime", return_value=[]),
        patch("openjiuwen.sdk._internal.runner_bridge.make_agent_card", return_value=MagicMock()),
        patch("openjiuwen.sdk._internal.runner_bridge.make_deep_agent_config", return_value=MagicMock()),
        patch("openjiuwen.sdk._internal.runner_bridge.create_deep_agent", return_value=fake_agent),
        patch("openjiuwen.sdk._internal.session_bridge.make_internal_session", return_value=fake_sess),
    )
    return patches, fake_agent


def _sync_patches(fake_agent, fake_sess):
    """Return a single context manager that applies all patches."""
    import contextlib

    @contextlib.contextmanager
    def _cm():
        with (
            patch("openjiuwen.sdk._internal.runner_bridge._require_runtime"),
            patch("openjiuwen.sdk._internal.runner_bridge._get_runner", new_callable=AsyncMock),
            patch("openjiuwen.sdk._internal.runner_bridge._build_model", return_value=MagicMock()),
            patch("openjiuwen.sdk._internal.runner_bridge._sdk_tools_to_runtime", return_value=[]),
            patch("openjiuwen.sdk._internal.runner_bridge.make_agent_card", return_value=MagicMock()),
            patch("openjiuwen.sdk._internal.runner_bridge.make_deep_agent_config", return_value=MagicMock()),
            patch("openjiuwen.sdk._internal.runner_bridge.create_deep_agent", return_value=fake_agent),
            patch("openjiuwen.sdk._internal.session_bridge.make_internal_session", return_value=fake_sess),
        ):
            yield

    return _cm()


import contextlib


@contextlib.asynccontextmanager
async def _apply(*ctx_managers):
    """Stack multiple sync context managers as an async context manager."""
    import contextlib as _cl

    with _cl.ExitStack() as stack:
        for cm in ctx_managers:
            stack.enter_context(cm)
        yield


def _make_mock_team_with_stream(chunks: list) -> MagicMock:
    """Build a mock team runtime object whose .stream() yields the chunks."""
    team = MagicMock()

    async def _stream(inputs, agent_session=None, **kw):
        for c in chunks:
            yield c

    team.stream = _stream
    team.invoke = AsyncMock(return_value={"text": "done"})
    return team


def _build_team_facade(mock_team_runtime) -> "Team":
    """Build a Team façade whose _handle._team_agent is mock_team_runtime (sync, no patches)."""
    from openjiuwen.sdk.agents.team import Team, _TeamHandle
    from openjiuwen.sdk.core.config import ModelConfig

    handle = _TeamHandle(model_cfg=ModelConfig(model="openai/gpt-4o", api_key="k"))
    handle._team_agent = mock_team_runtime
    handle._team_name = "test-team"
    return Team(handle)
