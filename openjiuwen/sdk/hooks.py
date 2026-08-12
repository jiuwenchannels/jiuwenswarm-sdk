"""Lifecycle hook registration for SDK agents.

``Hooks`` is a convenience wrapper around :class:`~openjiuwen.sdk.events.EventEmitter`.
Pass a configured ``Hooks`` instance to :meth:`Agent.create` and your callbacks
will be invoked at the appropriate points in the agent's lifecycle.

Quick start::

    from openjiuwen.sdk import Agent, ModelConfig
    from openjiuwen.sdk.hooks import Hooks

    hooks = Hooks()

    @hooks.on_token
    def print_token(token: str) -> None:
        print(token, end="", flush=True)

    @hooks.on_tool_call
    def log_tool(name: str, args: dict) -> None:
        print(f"\\n[tool] {name}({args})")

    agent = await Agent.create("my-agent", model=ModelConfig.from_env(), hooks=hooks)
    await agent.run("What is 2 + 2?")

Alternatively, pass callables directly::

    hooks = Hooks(
        on_token=lambda t: print(t, end=""),
        on_tool_call=lambda name, args: print(f"[tool] {name}"),
        on_done=lambda: print("\\n[done]"),
    )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Event names (string constants used by Agent's EventEmitter)
# ---------------------------------------------------------------------------

EVENT_TOKEN = "token"
EVENT_TOOL_CALL = "tool_call"
EVENT_TOOL_RESULT = "tool_result"
EVENT_DONE = "done"
EVENT_ERROR = "error"
EVENT_START = "start"


# ---------------------------------------------------------------------------
# Hooks — callable-slot container
# ---------------------------------------------------------------------------


@dataclass
class Hooks:
    """Collection of lifecycle callbacks for an :class:`~openjiuwen.sdk.agent.Agent`.

    Each slot is a *list* of callables so multiple subscribers can coexist.
    Use the decorator form (``@hooks.on_token``) or pass callables directly
    in the constructor.

    Args:
        on_token:       Called with ``(token: str)`` for each streamed token.
        on_tool_call:   Called with ``(name: str, args: dict)`` before a tool
                        is executed.
        on_tool_result: Called with ``(name: str, result: str)`` after a tool
                        returns.
        on_done:        Called with no arguments when the agent finishes a run.
        on_error:       Called with ``(error: Exception)`` on failure.
        on_start:       Called with ``(prompt: str)`` when a run begins.

    The callable arguments match the event payloads emitted by
    :class:`~openjiuwen.sdk.agent.Agent`.
    """

    # Mutable default lists — one list per slot, shared by all decorators.
    on_token: list[Callable[[str], Any]] = field(default_factory=list)
    on_tool_call: list[Callable[[str, dict], Any]] = field(default_factory=list)
    on_tool_result: list[Callable[[str, str], Any]] = field(default_factory=list)
    on_done: list[Callable[[], Any]] = field(default_factory=list)
    on_error: list[Callable[[Exception], Any]] = field(default_factory=list)
    on_start: list[Callable[[str], Any]] = field(default_factory=list)

    def __init__(
        self,
        *,
        on_token: "Callable[[str], Any] | list[Callable[[str], Any]] | None" = None,
        on_tool_call: "Callable[[str, dict], Any] | list[Callable[[str, dict], Any]] | None" = None,
        on_tool_result: "Callable[[str, str], Any] | list[Callable[[str, str], Any]] | None" = None,
        on_done: "Callable[[], Any] | list[Callable[[], Any]] | None" = None,
        on_error: "Callable[[Exception], Any] | list[Callable[[Exception], Any]] | None" = None,
        on_start: "Callable[[str], Any] | list[Callable[[str], Any]] | None" = None,
    ) -> None:
        self.on_token = _ensure_list(on_token)
        self.on_tool_call = _ensure_list(on_tool_call)
        self.on_tool_result = _ensure_list(on_tool_result)
        self.on_done = _ensure_list(on_done)
        self.on_error = _ensure_list(on_error)
        self.on_start = _ensure_list(on_start)

    # ------------------------------------------------------------------
    # Decorator helpers
    # ------------------------------------------------------------------

    def token(self, fn: Callable[[str], Any]) -> Callable[[str], Any]:
        """Register *fn* as an ``on_token`` callback (decorator form)."""
        self.on_token.append(fn)
        return fn

    def tool_call(self, fn: Callable[[str, dict], Any]) -> Callable[[str, dict], Any]:
        """Register *fn* as an ``on_tool_call`` callback."""
        self.on_tool_call.append(fn)
        return fn

    def tool_result(self, fn: Callable[[str, str], Any]) -> Callable[[str, str], Any]:
        """Register *fn* as an ``on_tool_result`` callback."""
        self.on_tool_result.append(fn)
        return fn

    def done(self, fn: Callable[[], Any]) -> Callable[[], Any]:
        """Register *fn* as an ``on_done`` callback."""
        self.on_done.append(fn)
        return fn

    def error(self, fn: Callable[[Exception], Any]) -> Callable[[Exception], Any]:
        """Register *fn* as an ``on_error`` callback."""
        self.on_error.append(fn)
        return fn

    def start(self, fn: Callable[[str], Any]) -> Callable[[str], Any]:
        """Register *fn* as an ``on_start`` callback."""
        self.on_start.append(fn)
        return fn

    # ------------------------------------------------------------------
    # Integration: wire into an EventEmitter (called by Agent)
    # ------------------------------------------------------------------

    def wire(self, emitter: Any) -> None:
        """Wire all registered callbacks into *emitter*.

        The *emitter* is an :class:`~openjiuwen.sdk.events.EventEmitter`.
        Called internally by :class:`~openjiuwen.sdk.agent.Agent` after
        construction.
        """
        for cb in self.on_token:
            emitter.on(EVENT_TOKEN, cb)
        for cb in self.on_tool_call:
            emitter.on(EVENT_TOOL_CALL, cb)
        for cb in self.on_tool_result:
            emitter.on(EVENT_TOOL_RESULT, cb)
        for cb in self.on_done:
            emitter.on(EVENT_DONE, cb)
        for cb in self.on_error:
            emitter.on(EVENT_ERROR, cb)
        for cb in self.on_start:
            emitter.on(EVENT_START, cb)

    def __repr__(self) -> str:
        total = (
            len(self.on_token)
            + len(self.on_tool_call)
            + len(self.on_tool_result)
            + len(self.on_done)
            + len(self.on_error)
            + len(self.on_start)
        )
        return f"Hooks(callbacks={total})"


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _ensure_list(value: Any) -> list:
    if value is None:
        return []
    if callable(value):
        return [value]
    return list(value)
