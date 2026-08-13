"""Tests for openjiuwen.sdk.core.events — EventEmitter."""

from __future__ import annotations

import asyncio

import pytest

from openjiuwen.sdk.core.events import EventEmitter


class TestEventEmitter:
    def test_on_and_emit(self):
        ee = EventEmitter()
        log: list = []
        ee.on("x", lambda v: log.append(v))
        ee.emit("x", 1)
        ee.emit("x", 2)
        assert log == [1, 2]

    def test_emit_unknown_event_noop(self):
        ee = EventEmitter()
        ee.emit("nothing")  # must not raise

    def test_off_removes_listener(self):
        ee = EventEmitter()
        log: list = []
        cb = lambda v: log.append(v)  # noqa: E731
        ee.on("y", cb)
        ee.emit("y", 10)
        ee.off("y", cb)
        ee.emit("y", 20)
        assert log == [10]

    def test_off_unknown_listener_noop(self):
        ee = EventEmitter()
        ee.off("nope", lambda: None)  # must not raise

    def test_off_all_single_event(self):
        ee = EventEmitter()
        log: list = []
        ee.on("a", lambda: log.append("a"))
        ee.on("b", lambda: log.append("b"))
        ee.off_all("a")
        ee.emit("a")
        ee.emit("b")
        assert log == ["b"]

    def test_off_all_clears_everything(self):
        ee = EventEmitter()
        log: list = []
        ee.on("a", lambda: log.append("a"))
        ee.on("b", lambda: log.append("b"))
        ee.off_all()
        ee.emit("a")
        ee.emit("b")
        assert log == []

    def test_multiple_listeners_same_event(self):
        ee = EventEmitter()
        log: list = []
        ee.on("e", lambda: log.append(1))
        ee.on("e", lambda: log.append(2))
        ee.on("e", lambda: log.append(3))
        ee.emit("e")
        assert log == [1, 2, 3]

    @pytest.mark.asyncio
    async def test_emit_async_awaits_async_callbacks(self):
        ee = EventEmitter()
        log: list = []

        async def async_cb(v):
            await asyncio.sleep(0)
            log.append(v)

        ee.on("z", async_cb)
        await ee.emit_async("z", 42)
        assert log == [42]

    @pytest.mark.asyncio
    async def test_emit_async_mixes_sync_and_async(self):
        ee = EventEmitter()
        log: list = []

        ee.on("m", lambda v: log.append(f"sync:{v}"))

        async def async_cb(v):
            log.append(f"async:{v}")

        ee.on("m", async_cb)
        await ee.emit_async("m", 7)
        assert log == ["sync:7", "async:7"]
