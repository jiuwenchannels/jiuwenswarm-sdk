"""Lightweight event-emitter mixin used by :class:`~openjiuwen.sdk.agent.Agent`.

Events emitted by an agent:

- ``"token"``       — ``(text: str)`` — a token arrived while streaming.
- ``"done"``        — ``()``          — the agent finished successfully.
- ``"error"``       — ``(msg: str)``  — the agent encountered an error.
- ``"tool_call"``   — ``(name: str, args: dict)`` — a tool call is about to run.
- ``"tool_result"`` — ``(name: str, result: str)`` — a tool call completed.
"""

from __future__ import annotations

import asyncio
import inspect
from collections import defaultdict
from typing import Any, Callable


class EventEmitter:
    """Synchronous/async event emitter used as a mixin."""

    def __init__(self) -> None:
        self._listeners: dict[str, list[Callable]] = defaultdict(list)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def on(self, event: str, callback: Callable) -> None:
        """Register *callback* for *event*.

        The same callback can be registered multiple times; it will fire
        once per registration per event.
        """
        self._listeners[event].append(callback)

    def off(self, event: str, callback: Callable) -> None:
        """Remove a previously registered *callback* for *event*.

        No-op if *callback* is not registered.
        """
        try:
            self._listeners[event].remove(callback)
        except ValueError:
            pass

    def off_all(self, event: str | None = None) -> None:
        """Remove all listeners for *event*, or all listeners if *event* is ``None``."""
        if event is None:
            self._listeners.clear()
        else:
            self._listeners.pop(event, None)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def emit(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Fire all callbacks registered for *event* synchronously.

        Async callbacks are scheduled on the running event loop (if any) and
        not awaited — use :meth:`emit_async` when you need to await them.
        """
        loop: asyncio.AbstractEventLoop | None = None
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            pass

        for cb in list(self._listeners.get(event, [])):
            if inspect.iscoroutinefunction(cb):
                if loop is not None:
                    loop.create_task(cb(*args, **kwargs))
                # If no loop is running, skip async callbacks silently.
            else:
                cb(*args, **kwargs)

    async def emit_async(self, event: str, *args: Any, **kwargs: Any) -> None:
        """Fire all callbacks for *event*, awaiting any async ones."""
        for cb in list(self._listeners.get(event, [])):
            if inspect.iscoroutinefunction(cb):
                await cb(*args, **kwargs)
            else:
                cb(*args, **kwargs)
