"""SDK Multi-Rollout façade — run the same prompt N times and pick the best result.

Quick start::

    from openjiuwen.sdk.rollout import MultiRolloutConfig, MultiRolloutExecutor

    executor = MultiRolloutExecutor(agent, MultiRolloutConfig(n=5, concurrency=3))
    results = await executor.run("Write a catchy tagline for a cloud product.")
    best = await executor.best_of(results, metric=LLMAsJudgeMetric(criteria="Most creative"))
    print(best.text)
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from openjiuwen.sdk.errors import SdkError

if TYPE_CHECKING:
    from openjiuwen.sdk.agent import Agent, AgentResult
    from openjiuwen.sdk.eval import EvalCase, Metric


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MultiRolloutConfig:
    """Configuration for a multi-rollout execution.

    Attributes:
        n:           Number of independent rollouts to perform.
        temperature: Sampling temperature (overrides the agent's default for diversity).
        concurrency: Maximum number of rollouts running in parallel.
        timeout:     Per-rollout timeout in seconds.
    """

    n: int = 3
    temperature: float | None = None
    concurrency: int = 3
    timeout: float | None = None


# ---------------------------------------------------------------------------
# Result
# ---------------------------------------------------------------------------


@dataclass
class RolloutResult:
    """A single rollout result.

    Attributes:
        text:        The agent's response text.
        session_id:  Session ID used for this rollout.
        rollout_idx: Zero-based index of this rollout within the batch.
        metadata:    Extra fields from the agent result.
    """

    text: str
    session_id: str | None = None
    rollout_idx: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# MultiRolloutExecutor
# ---------------------------------------------------------------------------


class MultiRolloutExecutor:
    """Executes an agent multiple times and aggregates results.

    Example::

        cfg = MultiRolloutConfig(n=5, temperature=0.9, concurrency=2)
        executor = MultiRolloutExecutor(agent, cfg)
        results = await executor.run("Write a haiku about AI.")
        best = await executor.best_of(results, metric=ExactMatchMetric())
    """

    def __init__(self, agent: "Agent", config: MultiRolloutConfig) -> None:
        self._agent = agent
        self._config = config

    async def run(
        self,
        prompt: str,
        *,
        session_id: str | None = None,
    ) -> list[RolloutResult]:
        """Execute *n* rollouts of *prompt* and return all results.

        Args:
            prompt:     The prompt to run.
            session_id: Optional shared session (if none, each rollout gets its own).

        Returns:
            List of :class:`RolloutResult` objects (length == ``config.n``).
        """
        if self._config.n < 1:
            raise SdkError("MultiRolloutConfig.n must be >= 1")

        semaphore = asyncio.Semaphore(max(1, self._config.concurrency))

        async def _single(idx: int) -> RolloutResult:
            async with semaphore:
                try:
                    if self._config.timeout is not None:
                        agent_result = await asyncio.wait_for(
                            self._agent.run(prompt, session_id=session_id),
                            timeout=self._config.timeout,
                        )
                    else:
                        agent_result = await self._agent.run(prompt, session_id=session_id)
                except asyncio.TimeoutError:
                    raise SdkError(
                        f"Rollout {idx} timed out after {self._config.timeout}s."
                    )
                return RolloutResult(
                    text=agent_result.text,
                    session_id=agent_result.session_id,
                    rollout_idx=idx,
                    metadata=agent_result.metadata,
                )

        tasks = [_single(i) for i in range(self._config.n)]
        results = await asyncio.gather(*tasks)
        return list(results)

    async def best_of(
        self,
        results: list[RolloutResult],
        *,
        metric: "Metric",
    ) -> RolloutResult:
        """Return the highest-scoring rollout result according to *metric*.

        Args:
            results: List returned by :meth:`run`.
            metric:  Any :class:`~openjiuwen.sdk.eval.Metric` instance.

        Returns:
            The :class:`RolloutResult` with the highest score.

        Raises:
            :class:`~openjiuwen.sdk.errors.SdkError`: If *results* is empty.
        """
        if not results:
            raise SdkError("best_of received an empty results list")

        from openjiuwen.sdk.eval import EvalCase

        scored: list[tuple[float, RolloutResult]] = []
        for r in results:
            case = EvalCase(input="", expected="", prediction=r.text)
            score = await metric.score(case)
            scored.append((score, r))

        scored.sort(key=lambda t: t[0], reverse=True)
        return scored[0][1]

    async def majority_vote(self, results: list[RolloutResult]) -> RolloutResult:
        """Return the rollout result that appears most frequently (exact text match).

        Args:
            results: List returned by :meth:`run`.

        Returns:
            The most common :class:`RolloutResult`.
        """
        if not results:
            raise SdkError("majority_vote received an empty results list")

        counts: dict[str, list[RolloutResult]] = {}
        for r in results:
            counts.setdefault(r.text, []).append(r)

        best_text = max(counts, key=lambda k: len(counts[k]))
        return counts[best_text][0]

    def __repr__(self) -> str:
        return f"MultiRolloutExecutor(n={self._config.n}, concurrency={self._config.concurrency})"
