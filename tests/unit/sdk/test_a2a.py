"""Tests for openjiuwen.sdk.agents.a2a — RemoteAgent client facade."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openjiuwen.sdk.agents.a2a import A2AError, A2AResult, RemoteAgent, _extract_text
from openjiuwen.sdk.core.errors import ConnectionError, StreamError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_fake_a2a_client(text: str = "remote answer") -> MagicMock:
    client = MagicMock()
    client.invoke = AsyncMock(return_value={"text": text})

    async def _stream(inputs):
        for word in text.split():
            yield {"text": word + " "}

    client.stream = _stream
    client.cancel_task = AsyncMock(return_value={"status": "cancelled"})
    client.stop = AsyncMock()
    return client


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mock_a2a(request):
    """Patch _create_a2a_client to return a fake client."""
    text = getattr(request, "param", "hello world")
    fake_client = _make_fake_a2a_client(text)

    with patch("openjiuwen.sdk.agents.a2a._create_a2a_client", return_value=fake_client):
        yield {"client": fake_client}


# ---------------------------------------------------------------------------
# RemoteAgent construction
# ---------------------------------------------------------------------------


class TestRemoteAgentConstruction:
    def test_constructor_stores_fields(self):
        agent = RemoteAgent("http://host:9000", "my-agent", auth_token="tok", timeout=30.0)
        assert agent._url == "http://host:9000"
        assert agent._agent_id == "my-agent"
        assert agent._auth_token == "tok"
        assert agent._timeout == 30.0

    def test_url_trailing_slash_stripped(self):
        agent = RemoteAgent("http://host:9000/", "svc")
        assert not agent._url.endswith("/")

    def test_default_timeout(self):
        agent = RemoteAgent("http://host:9000", "svc")
        assert agent._timeout == 60.0

    def test_repr(self):
        agent = RemoteAgent("http://host:9000", "svc")
        assert "host:9000" in repr(agent)
        assert "svc" in repr(agent)


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------


class TestRemoteAgentRun:
    @pytest.mark.asyncio
    async def test_run_returns_a2a_result(self, mock_a2a):
        agent = RemoteAgent("http://host:9000", "svc")
        result = await agent.run("hello")
        assert isinstance(result, A2AResult)

    @pytest.mark.asyncio
    async def test_run_extracts_text(self, mock_a2a):
        mock_a2a["client"].invoke = AsyncMock(return_value={"text": "the answer"})
        agent = RemoteAgent("http://host:9000", "svc")
        result = await agent.run("question")
        assert result.text == "the answer"

    @pytest.mark.asyncio
    async def test_run_passes_task_id_if_given(self, mock_a2a):
        agent = RemoteAgent("http://host:9000", "svc")
        result = await agent.run("q", task_id="tid_123")
        assert result.task_id == "tid_123"

    @pytest.mark.asyncio
    async def test_run_auto_generates_task_id(self, mock_a2a):
        agent = RemoteAgent("http://host:9000", "svc")
        result = await agent.run("q")
        assert result.task_id is not None
        assert result.task_id.startswith("task-")

    @pytest.mark.asyncio
    async def test_run_raises_a2a_error_on_failure(self, mock_a2a):
        mock_a2a["client"].invoke = AsyncMock(side_effect=RuntimeError("boom"))
        agent = RemoteAgent("http://host:9000", "svc")
        with pytest.raises(A2AError, match="boom"):
            await agent.run("q")

    @pytest.mark.asyncio
    async def test_run_raises_connection_error_when_no_extension(self):
        with patch("openjiuwen.sdk.agents.a2a._create_a2a_client", side_effect=ImportError("no a2a")):
            agent = RemoteAgent("http://host:9000", "svc")
            with pytest.raises(ConnectionError, match="A2A extension not installed"):
                await agent.run("q")


# ---------------------------------------------------------------------------
# stream()
# ---------------------------------------------------------------------------


class TestRemoteAgentStream:
    @pytest.mark.asyncio
    async def test_stream_yields_tokens(self, mock_a2a):
        async def _fake_stream(inputs):
            for t in ["hello ", "world "]:
                yield {"text": t}

        mock_a2a["client"].stream = _fake_stream
        agent = RemoteAgent("http://host:9000", "svc")
        tokens = [t async for t in agent.stream("q")]
        assert tokens == ["hello ", "world "]

    @pytest.mark.asyncio
    async def test_stream_raises_stream_error_on_failure(self, mock_a2a):
        async def _broken(inputs):
            raise RuntimeError("network error")
            yield  # make it a generator

        mock_a2a["client"].stream = _broken
        agent = RemoteAgent("http://host:9000", "svc")
        with pytest.raises(StreamError, match="network error"):
            async for _ in agent.stream("q"):
                pass

    @pytest.mark.asyncio
    async def test_stream_skips_empty_tokens(self, mock_a2a):
        async def _fake_stream(inputs):
            yield {"text": ""}
            yield {"text": "hi"}
            yield {"text": ""}

        mock_a2a["client"].stream = _fake_stream
        agent = RemoteAgent("http://host:9000", "svc")
        tokens = [t async for t in agent.stream("q")]
        assert tokens == ["hi"]


# ---------------------------------------------------------------------------
# cancel()
# ---------------------------------------------------------------------------


class TestRemoteAgentCancel:
    @pytest.mark.asyncio
    async def test_cancel_returns_true(self, mock_a2a):
        agent = RemoteAgent("http://host:9000", "svc")
        ok = await agent.cancel("task-abc")
        assert ok is True

    @pytest.mark.asyncio
    async def test_cancel_raises_a2a_error_on_failure(self, mock_a2a):
        mock_a2a["client"].cancel_task = AsyncMock(side_effect=RuntimeError("cancel fail"))
        agent = RemoteAgent("http://host:9000", "svc")
        with pytest.raises(A2AError, match="cancel fail"):
            await agent.cancel("task-abc")

    @pytest.mark.asyncio
    async def test_cancel_without_cancel_task_method(self, mock_a2a):
        del mock_a2a["client"].cancel_task  # remove cancel_task attribute
        agent = RemoteAgent("http://host:9000", "svc")
        ok = await agent.cancel("task-abc")
        assert ok is True


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestRemoteAgentContextManager:
    @pytest.mark.asyncio
    async def test_context_manager_closes(self, mock_a2a):
        async with RemoteAgent("http://host:9000", "svc") as agent:
            _ = await agent.run("q")
        # close() should have been called without error


# ---------------------------------------------------------------------------
# A2AResult
# ---------------------------------------------------------------------------


class TestA2AResult:
    def test_fields(self):
        r = A2AResult(text="ok", task_id="t1", metadata={"k": "v"})
        assert r.text == "ok"
        assert r.task_id == "t1"
        assert r.metadata == {"k": "v"}

    def test_defaults(self):
        r = A2AResult(text="ok")
        assert r.task_id is None
        assert r.metadata == {}


# ---------------------------------------------------------------------------
# _extract_text helper
# ---------------------------------------------------------------------------


class TestExtractText:
    def test_str_passthrough(self):
        assert _extract_text("hello") == "hello"

    def test_dict_text_key(self):
        assert _extract_text({"text": "hi"}) == "hi"

    def test_dict_content_key(self):
        assert _extract_text({"content": "hi"}) == "hi"

    def test_dict_fallback_joins_values(self):
        result = _extract_text({"a": "x", "b": "y"})
        assert "x" in result and "y" in result

    def test_object_with_text_attr(self):
        from types import SimpleNamespace
        obj = SimpleNamespace(text="from_attr")
        assert _extract_text(obj) == "from_attr"

    def test_unknown_falls_back_to_str(self):
        result = _extract_text(42)
        assert result == "42"
