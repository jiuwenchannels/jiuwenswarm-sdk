"""Swarm orchestration bridge.

Module-level patchable functions that wrap ``openjiuwen.harness`` swarm
primitives.
"""

from __future__ import annotations

import asyncio
from typing import Any


# ---------------------------------------------------------------------------
# Module-level patchable callables
# ---------------------------------------------------------------------------


async def run_parallel(tasks: list[Any]) -> list[str]:
    """Execute a list of agent callables concurrently (patchable)."""
    results = await asyncio.gather(*tasks, return_exceptions=True)
    out: list[str] = []
    for r in results:
        if isinstance(r, Exception):
            out.append(f"[error: {r}]")
        elif isinstance(r, str):
            out.append(r)
        else:
            out.append(str(r))
    return out


async def run_pipeline(tasks: list[Any]) -> str:
    """Execute a list of agent callables sequentially, chaining outputs (patchable)."""
    current_input: str | None = None
    for task_fn in tasks:
        if current_input is not None and callable(task_fn):
            result = await task_fn(current_input)
        elif callable(task_fn):
            result = await task_fn()
        else:
            result = str(task_fn)
        current_input = result if isinstance(result, str) else str(result)
    return current_input or ""


def select_best_of(results: list[str]) -> str:
    """Select the 'best' result by longest response heuristic (patchable)."""
    if not results:
        return ""
    return max(results, key=len)


def majority_vote(results: list[str]) -> str:
    """Select the most common result (patchable)."""
    if not results:
        return ""
    counts: dict[str, int] = {}
    for r in results:
        counts[r] = counts.get(r, 0) + 1
    return max(counts, key=lambda k: counts[k])
