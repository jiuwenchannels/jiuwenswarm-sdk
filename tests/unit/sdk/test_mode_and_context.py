"""Tests for AgentMode, ChannelId, and context_prefix.

Covers:
- AgentMode constant values and validation
- ChannelId constant values
- Agent._apply_context() — prompt prepending logic
- context_prefix forwarded through Agent.run() / stream() / stream_events()
- AgentMode / ChannelId importable from openjiuwen.sdk top-level
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from openjiuwen.sdk.core.agent import Agent, AgentResult
from openjiuwen.sdk.core.config import ModelConfig
from openjiuwen.sdk.core.mode import AgentMode, ChannelId
from openjiuwen.sdk.core.stream import DeltaEvent, DoneEvent


# ---------------------------------------------------------------------------
# AgentMode tests
# ---------------------------------------------------------------------------


class TestAgentMode:
    def test_constant_values(self):
        assert AgentMode.AGENT == "agent"
        assert AgentMode.CODE == "code"
        assert AgentMode.TEAM == "team"
        assert AgentMode.CODE_TEAM == "code.team"

    def test_default_alias(self):
        assert AgentMode.DEFAULT == AgentMode.AGENT

    def test_values_returns_all_modes(self):
        vals = AgentMode.values()
        assert set(vals) == {"agent", "code", "team", "code.team"}
        assert len(vals) == 4

    def test_validate_known_modes(self):
        for mode in ("agent", "code", "team", "code.team"):
            assert AgentMode.validate(mode) == mode

    def test_validate_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown AgentMode"):
            AgentMode.validate("turbo")

    def test_validate_empty_string_raises(self):
        with pytest.raises(ValueError):
            AgentMode.validate("")

    def test_validate_returns_value_unchanged(self):
        result = AgentMode.validate("code")
        assert result == "code"
        assert type(result) is str


# ---------------------------------------------------------------------------
# ChannelId tests
# ---------------------------------------------------------------------------


class TestChannelId:
    def test_constant_values(self):
        assert ChannelId.API == "api"
        assert ChannelId.JUPYTER == "jupyter"
        assert ChannelId.IDE == "ide"
        assert ChannelId.BROWSER == "browser"
        assert ChannelId.CLI == "cli"

    def test_values_returns_all_channels(self):
        vals = ChannelId.values()
        assert set(vals) == {"api", "jupyter", "ide", "browser", "cli"}
        assert len(vals) == 5

    def test_constants_are_strings(self):
        for attr in ("API", "JUPYTER", "IDE", "BROWSER", "CLI"):
            val = getattr(ChannelId, attr)
            assert isinstance(val, str)


# ---------------------------------------------------------------------------
# Top-level package importability
# ---------------------------------------------------------------------------


class TestTopLevelImports:
    def test_agent_mode_importable_from_sdk(self):
        from openjiuwen.sdk import AgentMode as AM
        assert AM.AGENT == "agent"

    def test_channel_id_importable_from_sdk(self):
        from openjiuwen.sdk import ChannelId as CI
        assert CI.API == "api"

    def test_agent_mode_in_core_init(self):
        from openjiuwen.sdk.core import AgentMode as AM
        assert AM.CODE == "code"

    def test_channel_id_in_core_init(self):
        from openjiuwen.sdk.core import ChannelId as CI
        assert CI.JUPYTER == "jupyter"


# ---------------------------------------------------------------------------
# Agent._apply_context() tests
# ---------------------------------------------------------------------------


class TestApplyContext:
    def test_no_context_returns_prompt_unchanged(self):
        result = Agent._apply_context("Hello", None)
        assert result == "Hello"

    def test_empty_context_returns_prompt_unchanged(self):
        result = Agent._apply_context("Hello", "")
        assert result == "Hello"

    def test_context_prepended_with_separator(self):
        result = Agent._apply_context("Question?", "# File\ncode here")
        assert result == "# File\ncode here\n\n---\n\nQuestion?"

    def test_trailing_whitespace_stripped_from_context(self):
        result = Agent._apply_context("Q", "ctx   \n  ")
        assert result == "ctx\n\n---\n\nQ"

    def test_prompt_preserved_exactly(self):
        prompt = "   leading spaces and\nnewlines\n"
        result = Agent._apply_context(prompt, "ctx")
        assert result.endswith(prompt)

    def test_separator_appears_once(self):
        result = Agent._apply_context("p", "ctx")
        assert result.count("---") == 1


# ---------------------------------------------------------------------------
# context_prefix forwarded through Agent.run()
# ---------------------------------------------------------------------------


def _make_agent_with_mock_handle(run_return="answer", stream_chunks=None):
    """Build an Agent backed by a fully mocked handle."""
    handle = MagicMock()
    handle.run = AsyncMock(
        return_value=AgentResult(text=run_return, session_id="s1", metadata={})
    )

    if stream_chunks is None:
        stream_chunks = [DeltaEvent(delta="hi"), DoneEvent(text="hi")]

    async def _stream(*a, **kw):
        for c in stream_chunks:
            yield c

    handle.stream = MagicMock(side_effect=_stream)
    handle.stream_events = MagicMock(side_effect=_stream)

    # Use the real __init__ so EventEmitter._listeners is properly initialised
    agent = Agent(handle, _mode="inprocess")
    agent._default_mode = None
    return agent, handle


class TestContextPrefixInRun:
    @pytest.mark.asyncio
    async def test_run_applies_context_prefix(self):
        agent, handle = _make_agent_with_mock_handle()
        await agent.run("What?", context_prefix="ctx info")
        call_args = handle.run.call_args
        prompt_used = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")
        assert "ctx info" in prompt_used
        assert "What?" in prompt_used
        assert "---" in prompt_used

    @pytest.mark.asyncio
    async def test_run_without_context_prefix_uses_prompt_as_is(self):
        agent, handle = _make_agent_with_mock_handle()
        await agent.run("Hello")
        call_args = handle.run.call_args
        prompt_used = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")
        assert prompt_used == "Hello"

    def test_run_sync_applies_context_prefix(self):
        agent, handle = _make_agent_with_mock_handle()
        agent.run_sync("Sync?", context_prefix="sync ctx")
        call_args = handle.run.call_args
        prompt_used = call_args[0][0] if call_args[0] else call_args[1].get("prompt", "")
        assert "sync ctx" in prompt_used
        assert "Sync?" in prompt_used


# ---------------------------------------------------------------------------
# context_prefix forwarded through Agent.stream()
# ---------------------------------------------------------------------------


class TestContextPrefixInStream:
    @pytest.mark.asyncio
    async def test_stream_applies_context_prefix(self):
        chunks = [DeltaEvent(delta="x"), DoneEvent(text="x")]
        agent, handle = _make_agent_with_mock_handle(stream_chunks=chunks)

        received_prompt: list[str] = []

        async def _stream(prompt, **kw):
            received_prompt.append(prompt)
            for c in chunks:
                yield c

        handle.stream = MagicMock(side_effect=_stream)

        async for _ in agent.stream("Q", context_prefix="prefix"):
            pass

        assert received_prompt, "stream was not called"
        assert "prefix" in received_prompt[0]
        assert "Q" in received_prompt[0]

    @pytest.mark.asyncio
    async def test_stream_no_context_prefix_passes_prompt_unchanged(self):
        chunks = [DeltaEvent(delta="x"), DoneEvent(text="x")]
        agent, handle = _make_agent_with_mock_handle(stream_chunks=chunks)

        received_prompt: list[str] = []

        async def _stream(prompt, **kw):
            received_prompt.append(prompt)
            for c in chunks:
                yield c

        handle.stream = MagicMock(side_effect=_stream)

        async for _ in agent.stream("Hello"):
            pass

        assert received_prompt[0] == "Hello"


# ---------------------------------------------------------------------------
# context_prefix forwarded through Agent.stream_events()
# ---------------------------------------------------------------------------


class TestContextPrefixInStreamEvents:
    @pytest.mark.asyncio
    async def test_stream_events_applies_context_prefix(self):
        chunks = [DeltaEvent(delta="y"), DoneEvent(text="y")]
        agent, handle = _make_agent_with_mock_handle(stream_chunks=chunks)

        received_prompt: list[str] = []

        async def _stream_events(prompt, **kw):
            received_prompt.append(prompt)
            for c in chunks:
                yield c

        handle.stream_events = MagicMock(side_effect=_stream_events)

        async for _ in agent.stream_events("Task", context_prefix="notebook cell"):
            pass

        assert received_prompt, "stream_events was not called"
        assert "notebook cell" in received_prompt[0]
        assert "Task" in received_prompt[0]
