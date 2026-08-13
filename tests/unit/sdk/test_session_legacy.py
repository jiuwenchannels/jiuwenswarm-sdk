"""Tests for openjiuwen.sdk.core.session — Session facade and session_bridge."""

from __future__ import annotations

import pytest

from openjiuwen.sdk.core.errors import SessionError
from openjiuwen.sdk.core.session import Message, Session


@pytest.fixture(autouse=True)
def _clean_registry():
    """Isolate each test by clearing the in-process session registry."""
    from openjiuwen.sdk._internal import session_bridge
    session_bridge._registry.clear()
    yield
    session_bridge._registry.clear()


class TestSessionCreate:
    @pytest.mark.asyncio
    async def test_creates_with_title(self):
        s = await Session.create("My research")
        assert s.title == "My research"
        assert s.id.startswith("sess_")

    @pytest.mark.asyncio
    async def test_default_mode(self):
        s = await Session.create("Test")
        assert s.mode == "default"

    @pytest.mark.asyncio
    async def test_custom_mode(self):
        s = await Session.create("Deep session", mode="deep")
        assert s.mode == "deep"

    @pytest.mark.asyncio
    async def test_created_at_is_timestamp(self):
        import time
        before = time.time()
        s = await Session.create("ts test")
        after = time.time()
        assert before <= s.created_at <= after


class TestSessionList:
    @pytest.mark.asyncio
    async def test_empty_initially(self):
        sessions = await Session.list()
        assert sessions == []

    @pytest.mark.asyncio
    async def test_returns_all_sessions(self):
        s1 = await Session.create("A")
        s2 = await Session.create("B")
        lst = await Session.list()
        ids = {s.id for s in lst}
        assert s1.id in ids
        assert s2.id in ids

    @pytest.mark.asyncio
    async def test_newest_first(self):
        import asyncio
        s1 = await Session.create("First")
        await asyncio.sleep(0.01)
        s2 = await Session.create("Second")
        lst = await Session.list()
        assert lst[0].id == s2.id


class TestSessionGet:
    @pytest.mark.asyncio
    async def test_get_existing(self):
        s = await Session.create("Lookup test")
        got = await Session.get(s.id)
        assert got.id == s.id
        assert got.title == s.title

    @pytest.mark.asyncio
    async def test_get_unknown_raises(self):
        with pytest.raises(SessionError, match="sess_notexist"):
            await Session.get("sess_notexist")


class TestSessionDelete:
    @pytest.mark.asyncio
    async def test_delete_removes_from_list(self):
        s = await Session.create("Temp")
        await s.delete()
        lst = await Session.list()
        assert not any(x.id == s.id for x in lst)

    @pytest.mark.asyncio
    async def test_double_delete_noop(self):
        s = await Session.create("Temp")
        await s.delete()
        await s.delete()  # must not raise


class TestSessionHistory:
    @pytest.mark.asyncio
    async def test_empty_history(self):
        s = await Session.create("Empty")
        history = await s.history()
        assert history == []

    @pytest.mark.asyncio
    async def test_messages_appended_by_bridge(self):
        from openjiuwen.sdk._internal.session_bridge import append_message

        s = await Session.create("With history")
        append_message(s.id, role="user", text="Hello")
        append_message(s.id, role="assistant", text="Hi there!")

        history = await s.history()
        assert len(history) == 2
        assert isinstance(history[0], Message)
        assert history[0].role == "user"
        assert history[0].text == "Hello"
        assert history[1].role == "assistant"


class TestSessionRepr:
    @pytest.mark.asyncio
    async def test_repr(self):
        s = await Session.create("Repr test")
        r = repr(s)
        assert "Session" in r
        assert s.id in r
