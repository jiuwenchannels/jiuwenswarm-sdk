"""SDK SwarmFlow functional API — structured parallel/pipeline/phase orchestration.

Write a SwarmFlow script as an async Python function, using the helpers
``parallel``, ``pipeline``, and ``phase`` to structure the work.

Quick start::

    from openjiuwen.sdk.agents.swarmflow import run_swarmflow, agent, parallel, pipeline

    async def run(args: dict) -> str:
        research = await parallel(
            agent("researcher", "Research topic A"),
            agent("researcher", "Research topic B"),
        )
        draft = await pipeline(
            agent("writer", f"Write using: {research}"),
            agent("editor", "Improve the draft"),
        )
        return draft

    result = await run_swarmflow(script=run, args={"topic": "AI"})
    print(result.final_output)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class ActivityRecord:
    """Record of one agent activity within a phase."""

    agent_name: str
    prompt: str
    output: str
    index: int = 0


@dataclass
class PhaseRecord:
    """Record of one phase (parallel/pipeline/phase) in a swarm run."""

    index: int
    kind: str  # "parallel" | "pipeline" | "phase"
    activities: list[ActivityRecord] = field(default_factory=list)
    output: str = ""


@dataclass
class SwarmFlowResult:
    """The result of a :func:`run_swarmflow` call.

    Attributes:
        final_output: The string returned by the script function.
        phases:       Ordered list of :class:`PhaseRecord` objects.
        metadata:     Extra fields.
    """

    final_output: str
    phases: list[PhaseRecord] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Context — tracks phases for reporting
# ---------------------------------------------------------------------------


class _SwarmFlowContext:
    def __init__(self, args: dict[str, Any]) -> None:
        self.args = args
        self.phases: list[PhaseRecord] = []
        self._phase_index = 0

    def _next_phase_idx(self) -> int:
        idx = self._phase_index
        self._phase_index += 1
        return idx


_ctx_var: _SwarmFlowContext | None = None


def _get_ctx() -> _SwarmFlowContext:
    if _ctx_var is None:
        raise RuntimeError("run_swarmflow context not active")
    return _ctx_var


# ---------------------------------------------------------------------------
# agent() — creates a lazy agent task
# ---------------------------------------------------------------------------


def agent(name: str, prompt: str) -> Coroutine[Any, Any, str]:
    """Create a lazy agent call (to be scheduled by :func:`parallel` or :func:`pipeline`).

    Args:
        name:   Agent name (looked up or created on demand).
        prompt: Task prompt sent to the agent.

    Returns:
        A coroutine that resolves to the agent's response text.
    """
    return _run_agent(name, prompt)


async def _run_agent(name: str, prompt: str) -> str:
    """Execute the named agent with the given prompt."""
    try:
        from openjiuwen.sdk.core.agent import Agent
        from openjiuwen.sdk.core.config import ModelConfig

        ag = await Agent.create(name, model=ModelConfig.from_env())
        result = await ag.run(prompt)
        return result.text
    except Exception as exc:  # noqa: BLE001
        return f"[{name} error: {exc}]"


# ---------------------------------------------------------------------------
# parallel() — fan-out
# ---------------------------------------------------------------------------


async def parallel(*tasks: Coroutine[Any, Any, str]) -> list[str]:
    """Execute *tasks* concurrently and return their results as a list.

    Args:
        tasks: Agent coroutines created via :func:`agent`.

    Returns:
        List of response strings in the same order as *tasks*.
    """
    results = await asyncio.gather(*tasks, return_exceptions=True)
    outputs: list[str] = []
    for r in results:
        if isinstance(r, Exception):
            outputs.append(f"[error: {r}]")
        else:
            outputs.append(str(r))

    try:
        ctx = _get_ctx()
        phase_idx = ctx._next_phase_idx()
        phase = PhaseRecord(
            index=phase_idx,
            kind="parallel",
            activities=[
                ActivityRecord(agent_name="agent", prompt="", output=o, index=i)
                for i, o in enumerate(outputs)
            ],
            output=" | ".join(outputs),
        )
        ctx.phases.append(phase)
    except RuntimeError:
        pass

    return outputs


# ---------------------------------------------------------------------------
# pipeline() — sequential chain
# ---------------------------------------------------------------------------


async def pipeline(*tasks: Coroutine[Any, Any, str]) -> str:
    """Execute *tasks* sequentially, each receiving the previous output.

    Args:
        tasks: Agent coroutines created via :func:`agent`.

    Returns:
        The final task's response string.
    """
    outputs: list[str] = []
    for task in tasks:
        result = await task
        outputs.append(str(result) if not isinstance(result, Exception) else f"[error: {result}]")

    try:
        ctx = _get_ctx()
        phase_idx = ctx._next_phase_idx()
        phase = PhaseRecord(
            index=phase_idx,
            kind="pipeline",
            activities=[
                ActivityRecord(agent_name="agent", prompt="", output=o, index=i)
                for i, o in enumerate(outputs)
            ],
            output=outputs[-1] if outputs else "",
        )
        ctx.phases.append(phase)
    except RuntimeError:
        pass

    return outputs[-1] if outputs else ""


# ---------------------------------------------------------------------------
# phase() — named phase grouping
# ---------------------------------------------------------------------------


async def phase(name: str, *tasks: Coroutine[Any, Any, str]) -> list[str]:
    """Execute *tasks* as a named phase (for reporting purposes).

    Args:
        name:  Phase label (used in :class:`PhaseRecord`).
        tasks: Agent coroutines created via :func:`agent`.

    Returns:
        List of response strings.
    """
    results = await parallel(*tasks)

    try:
        ctx = _get_ctx()
        if ctx.phases:
            ctx.phases[-1].kind = f"phase:{name}"
    except RuntimeError:
        pass

    return results


# ---------------------------------------------------------------------------
# run_swarmflow() — entry point
# ---------------------------------------------------------------------------


async def run_swarmflow(
    *,
    script: Callable[..., Coroutine[Any, Any, str]],
    args: dict[str, Any] | None = None,
    meta: dict[str, Any] | None = None,
) -> SwarmFlowResult:
    """Execute a SwarmFlow script and return the aggregated result.

    The *script* is an async function that accepts a single ``args`` dict
    and may use :func:`parallel`, :func:`pipeline`, and :func:`phase` to
    structure its work.

    Args:
        script: Async function implementing the swarm logic.
        args:   Dictionary of input arguments passed to *script*.
        meta:   Metadata attached to the :class:`SwarmFlowResult`.

    Returns:
        :class:`SwarmFlowResult` with ``final_output`` and ``phases``.

    Example::

        async def my_script(args: dict) -> str:
            results = await parallel(
                agent("researcher", f"Research {args['topic']}"),
            )
            return results[0]

        result = await run_swarmflow(script=my_script, args={"topic": "AI"})
    """
    global _ctx_var  # noqa: PLW0603

    ctx = _SwarmFlowContext(args or {})
    _ctx_var = ctx

    try:
        final_output = await script(args or {})
    finally:
        _ctx_var = None

    return SwarmFlowResult(
        final_output=str(final_output),
        phases=ctx.phases,
        metadata=meta or {},
    )
