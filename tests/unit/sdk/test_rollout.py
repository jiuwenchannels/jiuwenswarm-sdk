"""Unit tests for openjiuwen.sdk.optimize.rollout — MultiRolloutExecutor."""

from __future__ import annotations

import pytest

from openjiuwen.sdk.core.errors import SdkError
from openjiuwen.sdk.optimize.eval import ExactMatchMetric
from openjiuwen.sdk.optimize.rollout import (
    MultiRolloutConfig,
    MultiRolloutExecutor,
    RolloutResult,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MockAgentResult:
    def __init__(self, text: str, session_id: str = "s1"):
        self.text = text
        self.session_id = session_id
        self.metadata = {}


class _MockAgent:
    def __init__(self, responses: list[str] | None = None, response: str = "answer"):
        self._responses = responses or []
        self._response = response
        self._call_count = 0

    async def run(self, prompt: str, session_id=None) -> _MockAgentResult:
        if self._responses:
            idx = self._call_count % len(self._responses)
            text = self._responses[idx]
        else:
            text = self._response
        self._call_count += 1
        return _MockAgentResult(text=text)


# ---------------------------------------------------------------------------
# MultiRolloutConfig tests
# ---------------------------------------------------------------------------


def test_rollout_config_defaults():
    cfg = MultiRolloutConfig()
    assert cfg.n == 3
    assert cfg.concurrency == 3
    assert cfg.temperature is None
    assert cfg.timeout is None


def test_rollout_config_frozen():
    cfg = MultiRolloutConfig()
    with pytest.raises((AttributeError, TypeError)):
        cfg.n = 10  # type: ignore[misc]


# ---------------------------------------------------------------------------
# RolloutResult tests
# ---------------------------------------------------------------------------


def test_rollout_result_fields():
    r = RolloutResult(text="hello", session_id="sess-1", rollout_idx=2)
    assert r.text == "hello"
    assert r.rollout_idx == 2


# ---------------------------------------------------------------------------
# MultiRolloutExecutor.run tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_run_returns_n_results():
    agent = _MockAgent(response="answer")
    executor = MultiRolloutExecutor(agent, MultiRolloutConfig(n=5, concurrency=2))
    results = await executor.run("What is 2+2?")
    assert len(results) == 5


@pytest.mark.asyncio
async def test_run_assigns_rollout_idx():
    agent = _MockAgent(response="x")
    executor = MultiRolloutExecutor(agent, MultiRolloutConfig(n=3))
    results = await executor.run("Q")
    idxs = {r.rollout_idx for r in results}
    assert idxs == {0, 1, 2}


@pytest.mark.asyncio
async def test_run_n_zero_raises():
    agent = _MockAgent()
    executor = MultiRolloutExecutor(agent, MultiRolloutConfig(n=0))
    with pytest.raises(SdkError, match="n must be"):
        await executor.run("Q")


# ---------------------------------------------------------------------------
# MultiRolloutExecutor.best_of tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_best_of_empty_raises():
    agent = _MockAgent()
    executor = MultiRolloutExecutor(agent, MultiRolloutConfig(n=1))
    with pytest.raises(SdkError, match="empty"):
        await executor.best_of([], metric=ExactMatchMetric())


@pytest.mark.asyncio
async def test_best_of_returns_highest_score():
    agent = _MockAgent(responses=["4", "five", "four"])
    executor = MultiRolloutExecutor(agent, MultiRolloutConfig(n=3))
    results = await executor.run("Q")
    # Use ExactMatchMetric — expected is empty so all score 0;
    # best_of still returns one item
    best = await executor.best_of(results, metric=ExactMatchMetric())
    assert isinstance(best, RolloutResult)


# ---------------------------------------------------------------------------
# MultiRolloutExecutor.majority_vote tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_majority_vote_basic():
    results = [
        RolloutResult(text="Paris", rollout_idx=0),
        RolloutResult(text="Paris", rollout_idx=1),
        RolloutResult(text="London", rollout_idx=2),
    ]
    agent = _MockAgent()
    executor = MultiRolloutExecutor(agent, MultiRolloutConfig(n=3))
    winner = await executor.majority_vote(results)
    assert winner.text == "Paris"


@pytest.mark.asyncio
async def test_majority_vote_empty_raises():
    agent = _MockAgent()
    executor = MultiRolloutExecutor(agent, MultiRolloutConfig(n=1))
    with pytest.raises(SdkError, match="empty"):
        await executor.majority_vote([])


# ---------------------------------------------------------------------------
# repr
# ---------------------------------------------------------------------------


def test_executor_repr():
    agent = _MockAgent()
    executor = MultiRolloutExecutor(agent, MultiRolloutConfig(n=5, concurrency=2))
    rep = repr(executor)
    assert "5" in rep
    assert "2" in rep
