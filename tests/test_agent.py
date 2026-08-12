"""Tests for openjiuwen.sdk.agent — Agent facade.

In-process tests mock the entire runtime layer (runner_bridge functions) so
no real LLM or server is needed.  Remote tests verify connection-failure
handling without a live server.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openjiuwen.sdk.agent import Agent, AgentResult
from openjiuwen.sdk.config import ModelConfig, RemoteConfig
from openjiuwen.sdk.errors import AgentError, ConnectionError, SessionError
from openjiuwen.sdk.tools import tool


# ---------------------------------------------------------------------------
# Fake runtime objects
# ---------------------------------------------------------------------------


def _make_fake_deep_agent(response: str = "fake answer") -> MagicMock:
    """Return a mock DeepAgent that returns a fixed response."""
    agent = MagicMock()
    agent.invoke = AsyncMock(return_value={"text": response})

    async def _stream(inputs, agent_session=None, **kw):
        for word in response.split():
            yield {"text": word + " "}

    agent.stream = _stream
    return agent


def _make_fake_session() -> MagicMock:
    sess = MagicMock()
    sess.pre_run = AsyncMock()
    sess.post_run = AsyncMock()
    sess.get_session_id = MagicMock(return_value="sess_fake")
    return sess


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_registry():
    """Isolate session registry between tests."""
    from openjiuwen.sdk._internal import session_bridge
    session_bridge._registry.clear()
    yield
    session_bridge._registry.clear()


@pytest.fixture()
def mock_runtime(request):
    """Patch all runtime callables in runner_bridge + session_bridge.

    Injects a ``fake_agent`` attribute so tests can customise its behaviour.
    """
    response = getattr(request, "param", "fake answer")
    fake_agent = _make_fake_deep_agent(response)
    fake_sess = _make_fake_session()

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
        # Expose the fakes so individual tests can inspect or override them.
        yield {"agent": fake_agent, "session": fake_sess}


# ---------------------------------------------------------------------------
# In-process Agent.create — basic lifecycle
# ---------------------------------------------------------------------------


class TestAgentCreate:
    @pytest.mark.asyncio
    async def test_create_returns_agent(self, mock_runtime):
        agent = await Agent.create("test", model=ModelConfig(api_key="x"))
        assert isinstance(agent, Agent)
        assert agent._mode == "inprocess"

    @pytest.mark.asyncio
    async def test_create_uses_model_from_env_if_none(self, mock_runtime):
        with patch(
            "openjiuwen.sdk._internal.runner_bridge._build_model",
            return_value=MagicMock(),
        ) as mock_build:
            agent = await Agent.create("test")  # model=None → ModelConfig.from_env()
            assert agent is not None
            mock_build.assert_called_once()

    @pytest.mark.asyncio
    async def test_repr(self, mock_runtime):
        agent = await Agent.create("my-agent", model=ModelConfig(api_key="x"))
        assert "my-agent" in repr(agent)
        assert "inprocess" in repr(agent)

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_runtime):
        async with await Agent.create("test", model=ModelConfig(api_key="x")) as agent:
            assert agent._mode == "inprocess"


# ---------------------------------------------------------------------------
# In-process Agent.run
# ---------------------------------------------------------------------------


class TestAgentRun:
    @pytest.mark.asyncio
    async def test_run_returns_agent_result(self, mock_runtime):
        mock_runtime["agent"].invoke = AsyncMock(return_value={"text": "Hello world"})
        agent = await Agent.create("test", model=ModelConfig(api_key="x"))
        result = await agent.run("Say hello")

        assert isinstance(result, AgentResult)
        assert result.text == "Hello world"
        assert result.session_id is not None

    @pytest.mark.asyncio
    async def test_run_emits_done_event(self, mock_runtime):
        events: list = []
        agent = await Agent.create("test", model=ModelConfig(api_key="x"))
        agent.on("done", lambda: events.append("done"))
        await agent.run("prompt")
        assert "done" in events

    @pytest.mark.asyncio
    async def test_run_creates_session_automatically(self, mock_runtime):
        from openjiuwen.sdk._internal import session_bridge
        agent = await Agent.create("test", model=ModelConfig(api_key="x"))
        result = await agent.run("first prompt")
        assert result.session_id is not None
        assert session_bridge.get_session(result.session_id) is not None

    @pytest.mark.asyncio
    async def test_run_reuses_session_across_calls(self, mock_runtime):
        agent = await Agent.create("test", model=ModelConfig(api_key="x"))
        r1 = await agent.run("first")
        r2 = await agent.run("second", session_id=r1.session_id)
        assert r1.session_id == r2.session_id

    @pytest.mark.asyncio
    async def test_run_records_message_history(self, mock_runtime):
        mock_runtime["agent"].invoke = AsyncMock(return_value={"text": "answer"})
        from openjiuwen.sdk._internal import session_bridge
        agent = await Agent.create("test", model=ModelConfig(api_key="x"))
        result = await agent.run("question")
        record = session_bridge.get_session(result.session_id)
        assert record is not None
        roles = [m.role for m in record.messages]
        assert "user" in roles
        assert "assistant" in roles

    @pytest.mark.asyncio
    async def test_run_raises_agent_error_on_failure(self, mock_runtime):
        mock_runtime["agent"].invoke = AsyncMock(side_effect=RuntimeError("boom"))
        agent = await Agent.create("test", model=ModelConfig(api_key="x"))
        with pytest.raises(AgentError, match="boom"):
            await agent.run("fail me")

    @pytest.mark.asyncio
    async def test_run_unknown_session_raises_session_error(self, mock_runtime):
        agent = await Agent.create("test", model=ModelConfig(api_key="x"))
        with pytest.raises(SessionError):
            await agent.run("prompt", session_id="sess_doesnotexist")

    @pytest.mark.asyncio
    async def test_run_with_tools_attached(self, mock_runtime):
        @tool
        def word_count(text: str) -> int:
            """Count words."""
            return len(text.split())

        mock_runtime["agent"].invoke = AsyncMock(return_value={"text": "3"})
        agent = await Agent.create(
            "test", model=ModelConfig(api_key="x"), tools=[word_count]
        )
        result = await agent.run("How many words in 'a b c'?")
        assert result.text == "3"

    def test_run_sync_outside_loop(self, mock_runtime):
        """run_sync must work without a running event loop."""
        import asyncio as aio

        async def _make():
            return await Agent.create("test", model=ModelConfig(api_key="x"))

        agent = aio.run(_make())
        # run_sync spawns a thread; mock_runtime is still active.
        result = agent.run_sync("hello")
        assert isinstance(result, AgentResult)


# ---------------------------------------------------------------------------
# In-process Agent.stream
# ---------------------------------------------------------------------------


class TestAgentStream:
    @pytest.mark.asyncio
    async def test_stream_yields_tokens(self, mock_runtime):
        async def _stream(inputs, agent_session=None, **kw):
            for t in ["hello ", "world "]:
                yield {"text": t}

        mock_runtime["agent"].stream = _stream
        agent = await Agent.create("test", model=ModelConfig(api_key="x"))
        tokens = [tok async for tok in agent.stream("say something")]
        assert tokens == ["hello ", "world "]

    @pytest.mark.asyncio
    async def test_stream_emits_token_events(self, mock_runtime):
        async def _stream(inputs, agent_session=None, **kw):
            yield {"text": "hi"}

        mock_runtime["agent"].stream = _stream
        emitted: list = []
        agent = await Agent.create("test", model=ModelConfig(api_key="x"))
        agent.on("token", lambda t: emitted.append(t))
        async for _ in agent.stream("anything"):
            pass
        assert "hi" in emitted

    @pytest.mark.asyncio
    async def test_stream_emits_done_event(self, mock_runtime):
        async def _stream(inputs, agent_session=None, **kw):
            yield {"text": "x"}

        mock_runtime["agent"].stream = _stream
        events: list = []
        agent = await Agent.create("test", model=ModelConfig(api_key="x"))
        agent.on("done", lambda: events.append("done"))
        async for _ in agent.stream("prompt"):
            pass
        assert "done" in events

    @pytest.mark.asyncio
    async def test_stream_records_history(self, mock_runtime):
        async def _stream(inputs, agent_session=None, **kw):
            yield {"text": "resp"}

        mock_runtime["agent"].stream = _stream
        from openjiuwen.sdk._internal import session_bridge
        agent = await Agent.create("test", model=ModelConfig(api_key="x"))
        sid = None
        async for tok in agent.stream("question"):
            # Pick up the session_id from the first token (not directly
            # exposed in stream; we get it from the registry after).
            pass
        # The bridge should have created a session.
        sessions = session_bridge.list_sessions()
        assert sessions, "No session created during stream"
        record = sessions[0]
        assert any(m.role == "assistant" for m in record.messages)


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------


class TestAgentCheckpoint:
    @pytest.mark.asyncio
    async def test_checkpoint_returns_id(self, mock_runtime):
        agent = await Agent.create("test", model=ModelConfig(api_key="x"))
        ckpt_id = await agent.checkpoint()
        assert ckpt_id.startswith("ckpt_")

    @pytest.mark.asyncio
    async def test_checkpoint_remote_raises(self):
        with pytest.raises(ConnectionError):
            remote = await Agent.connect("ws://localhost:19999/v1/ws")
        # Remote connect failed — checkpoint raises AgentError if somehow connected.
        # Just verify ConnectionError is raised on connect.


# ---------------------------------------------------------------------------
# Remote Agent.connect
# ---------------------------------------------------------------------------


class TestAgentConnect:
    @pytest.mark.asyncio
    async def test_connect_raises_on_unavailable_server(self):
        with pytest.raises(ConnectionError):
            await Agent.connect("ws://localhost:19999/v1/ws")

    @pytest.mark.asyncio
    async def test_connect_uses_remote_config(self):
        with pytest.raises(ConnectionError):
            cfg = RemoteConfig(server_url="ws://localhost:19999/v1/ws")
            await Agent.connect("ws://localhost:19999/v1/ws", config=cfg)


# ---------------------------------------------------------------------------
# AgentResult
# ---------------------------------------------------------------------------


class TestAgentResult:
    def test_fields(self):
        r = AgentResult(text="hello", session_id="sess_1")
        assert r.text == "hello"
        assert r.session_id == "sess_1"
        assert r.metadata == {}

    def test_default_metadata(self):
        assert AgentResult(text="x").metadata == {}


# ---------------------------------------------------------------------------
# sync_wrapper
# ---------------------------------------------------------------------------


class TestSyncWrapper:
    def test_run_sync_outside_loop(self):
        from openjiuwen.sdk._internal.sync_wrapper import run_sync

        async def coro():
            return 42

        assert run_sync(coro()) == 42

    def test_run_sync_inside_loop(self):
        from openjiuwen.sdk._internal.sync_wrapper import run_sync

        async def coro():
            return "nested"

        async def outer():
            return run_sync(coro())

        assert asyncio.run(outer()) == "nested"

    def test_run_sync_propagates_exception(self):
        from openjiuwen.sdk._internal.sync_wrapper import run_sync

        async def boom():
            raise ValueError("oops")

        with pytest.raises(ValueError, match="oops"):
            run_sync(boom())
