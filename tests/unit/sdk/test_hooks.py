"""Tests for openjiuwen.sdk.core.hooks — Hooks lifecycle-callback container."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from openjiuwen.sdk.core.hooks import (
    EVENT_DONE,
    EVENT_ERROR,
    EVENT_START,
    EVENT_TOKEN,
    EVENT_TOOL_CALL,
    EVENT_TOOL_RESULT,
    Hooks,
    _ensure_list,
)


# ---------------------------------------------------------------------------
# _ensure_list helper
# ---------------------------------------------------------------------------


class TestEnsureList:
    def test_none_returns_empty_list(self):
        assert _ensure_list(None) == []

    def test_callable_wrapped_in_list(self):
        fn = lambda: None  # noqa: E731
        result = _ensure_list(fn)
        assert result == [fn]

    def test_list_passthrough(self):
        fns = [lambda: 1, lambda: 2]  # noqa: E731
        assert _ensure_list(fns) == fns


# ---------------------------------------------------------------------------
# Hooks construction
# ---------------------------------------------------------------------------


class TestHooksConstruction:
    def test_empty_hooks(self):
        h = Hooks()
        assert h.on_token == []
        assert h.on_tool_call == []
        assert h.on_tool_result == []
        assert h.on_done == []
        assert h.on_error == []
        assert h.on_start == []

    def test_single_callable_constructor(self):
        fn = lambda t: None  # noqa: E731
        h = Hooks(on_token=fn)
        assert h.on_token == [fn]

    def test_list_constructor(self):
        fn1 = lambda t: None  # noqa: E731
        fn2 = lambda t: None  # noqa: E731
        h = Hooks(on_token=[fn1, fn2])
        assert h.on_token == [fn1, fn2]

    def test_all_slots_via_constructor(self):
        token_cb = lambda t: None  # noqa: E731
        tool_cb = lambda n, a: None  # noqa: E731
        result_cb = lambda n, r: None  # noqa: E731
        done_cb = lambda: None  # noqa: E731
        error_cb = lambda e: None  # noqa: E731
        start_cb = lambda p: None  # noqa: E731

        h = Hooks(
            on_token=token_cb,
            on_tool_call=tool_cb,
            on_tool_result=result_cb,
            on_done=done_cb,
            on_error=error_cb,
            on_start=start_cb,
        )
        assert h.on_token == [token_cb]
        assert h.on_tool_call == [tool_cb]
        assert h.on_tool_result == [result_cb]
        assert h.on_done == [done_cb]
        assert h.on_error == [error_cb]
        assert h.on_start == [start_cb]

    def test_repr(self):
        fn = lambda: None  # noqa: E731
        h = Hooks(on_token=fn, on_done=fn)
        r = repr(h)
        assert "Hooks" in r
        assert "callbacks=2" in r


# ---------------------------------------------------------------------------
# Decorator forms
# ---------------------------------------------------------------------------


class TestHooksDecorators:
    def test_token_decorator_appends(self):
        h = Hooks()
        log: list = []

        @h.token
        def cb(t: str) -> None:
            log.append(t)

        assert cb in h.on_token

    def test_token_decorator_returns_fn(self):
        h = Hooks()
        fn = lambda t: None  # noqa: E731
        result = h.token(fn)
        assert result is fn

    def test_tool_call_decorator(self):
        h = Hooks()
        fn = lambda n, a: None  # noqa: E731
        h.tool_call(fn)
        assert fn in h.on_tool_call

    def test_tool_result_decorator(self):
        h = Hooks()
        fn = lambda n, r: None  # noqa: E731
        h.tool_result(fn)
        assert fn in h.on_tool_result

    def test_done_decorator(self):
        h = Hooks()
        fn = lambda: None  # noqa: E731
        h.done(fn)
        assert fn in h.on_done

    def test_error_decorator(self):
        h = Hooks()
        fn = lambda e: None  # noqa: E731
        h.error(fn)
        assert fn in h.on_error

    def test_start_decorator(self):
        h = Hooks()
        fn = lambda p: None  # noqa: E731
        h.start(fn)
        assert fn in h.on_start

    def test_multiple_token_callbacks(self):
        h = Hooks()
        fn1 = lambda t: None  # noqa: E731
        fn2 = lambda t: None  # noqa: E731
        h.token(fn1)
        h.token(fn2)
        assert h.on_token == [fn1, fn2]


# ---------------------------------------------------------------------------
# Hooks.wire — binds to EventEmitter
# ---------------------------------------------------------------------------


class TestHooksWire:
    def test_wire_registers_token_cb(self):
        from openjiuwen.sdk.core.events import EventEmitter

        log: list = []
        h = Hooks(on_token=lambda t: log.append(t))
        ee = EventEmitter()
        h.wire(ee)
        ee.emit(EVENT_TOKEN, "hello")
        assert log == ["hello"]

    def test_wire_registers_done_cb(self):
        from openjiuwen.sdk.core.events import EventEmitter

        log: list = []
        h = Hooks(on_done=lambda: log.append("done"))
        ee = EventEmitter()
        h.wire(ee)
        ee.emit(EVENT_DONE)
        assert log == ["done"]

    def test_wire_registers_tool_call_cb(self):
        from openjiuwen.sdk.core.events import EventEmitter

        calls: list = []
        h = Hooks(on_tool_call=lambda name, args: calls.append((name, args)))
        ee = EventEmitter()
        h.wire(ee)
        ee.emit(EVENT_TOOL_CALL, "search", {"q": "test"})
        assert calls == [("search", {"q": "test"})]

    def test_wire_registers_error_cb(self):
        from openjiuwen.sdk.core.events import EventEmitter

        errors: list = []
        h = Hooks(on_error=lambda e: errors.append(str(e)))
        ee = EventEmitter()
        h.wire(ee)
        ee.emit(EVENT_ERROR, ValueError("oops"))
        assert errors == ["oops"]

    def test_wire_multiple_token_callbacks(self):
        from openjiuwen.sdk.core.events import EventEmitter

        log: list = []
        h = Hooks()
        h.token(lambda t: log.append(f"a:{t}"))
        h.token(lambda t: log.append(f"b:{t}"))
        ee = EventEmitter()
        h.wire(ee)
        ee.emit(EVENT_TOKEN, "x")
        assert log == ["a:x", "b:x"]

    def test_wire_empty_hooks_noop(self):
        from openjiuwen.sdk.core.events import EventEmitter

        h = Hooks()
        ee = EventEmitter()
        h.wire(ee)  # should not raise
        ee.emit(EVENT_TOKEN, "x")  # should not raise


# ---------------------------------------------------------------------------
# Integration: Hooks + Agent.create
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clean_registry():
    from openjiuwen.sdk._internal import session_bridge
    session_bridge._registry.clear()
    yield
    session_bridge._registry.clear()


@pytest.fixture()
def mock_runtime():
    """Same fixture used in test_agent.py — reused here for Agent.create."""
    from unittest.mock import AsyncMock, MagicMock

    fake_agent = MagicMock()
    fake_agent.invoke = AsyncMock(return_value={"text": "result"})

    async def _stream(inputs, agent_session=None, **kw):
        yield {"text": "tok"}

    fake_agent.stream = _stream

    fake_sess = MagicMock()
    fake_sess.pre_run = AsyncMock()
    fake_sess.post_run = AsyncMock()
    fake_sess.get_session_id = MagicMock(return_value="sess_fake")

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
        yield {"agent": fake_agent, "session": fake_sess}


class TestHooksWithAgent:
    @pytest.mark.asyncio
    async def test_hooks_token_fired_during_stream(self, mock_runtime):
        from openjiuwen.sdk import Agent, ModelConfig

        tokens: list = []
        h = Hooks(on_token=lambda t: tokens.append(t))
        agent = await Agent.create("test", model=ModelConfig(api_key="x"), hooks=h)
        async for _ in agent.stream("hi"):
            pass
        assert "tok" in tokens

    @pytest.mark.asyncio
    async def test_hooks_done_fired_after_run(self, mock_runtime):
        from openjiuwen.sdk import Agent, ModelConfig

        done_calls: list = []
        h = Hooks(on_done=lambda: done_calls.append(True))
        agent = await Agent.create("test", model=ModelConfig(api_key="x"), hooks=h)
        await agent.run("hi")
        assert done_calls == [True]

    @pytest.mark.asyncio
    async def test_hooks_wired_to_emitter(self, mock_runtime):
        from openjiuwen.sdk import Agent, ModelConfig

        log: list = []
        h = Hooks(on_token=lambda t: log.append(f"hook:{t}"))
        agent = await Agent.create("test", model=ModelConfig(api_key="x"), hooks=h)
        # Verify the hook is registered on the agent's emitter
        assert h.on_token[0] in agent._listeners.get(EVENT_TOKEN, [])
