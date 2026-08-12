"""Sync-from-async helpers for the SDK's convenience ``run_sync()`` methods.

Developers who don't want to manage an event loop can call::

    result = agent.run_sync("Hello!")

This module provides :func:`run_sync` which executes an async coroutine in a
way that is safe whether or not an event loop is already running.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any, Coroutine, TypeVar

T = TypeVar("T")


def run_sync(coro: Coroutine[Any, Any, T]) -> T:
    """Run *coro* synchronously, regardless of the current async context.

    - If **no** event loop is running (typical script / REPL use), uses
      :func:`asyncio.run`.
    - If an event loop **is** running (e.g. called from a Jupyter cell that
      already has a loop), spawns a new thread with its own event loop and
      blocks until the result is ready.

    Args:
        coro: The coroutine to run.

    Returns:
        The coroutine's return value.

    Raises:
        Any exception raised by *coro* is re-raised here.
    """
    try:
        asyncio.get_running_loop()
        # A loop is already running — we cannot use asyncio.run().
        return _run_in_thread(coro)
    except RuntimeError:
        # No loop running — safe to use asyncio.run().
        return asyncio.run(coro)


def _run_in_thread(coro: Coroutine[Any, Any, T]) -> T:
    result: T
    exc: BaseException | None = None

    def _target() -> None:
        nonlocal result, exc
        try:
            result = asyncio.run(coro)
        except BaseException as e:  # noqa: BLE001
            exc = e

    t = threading.Thread(target=_target, daemon=True)
    t.start()
    t.join()
    if exc is not None:
        raise exc  # type: ignore[misc]
    return result  # type: ignore[return-value]
