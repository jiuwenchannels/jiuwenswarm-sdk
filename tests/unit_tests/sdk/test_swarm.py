"""Unit tests for openjiuwen.sdk.swarm — SwarmFlow."""

from __future__ import annotations

import pytest

from openjiuwen.sdk.errors import SdkError
from openjiuwen.sdk.swarm import SwarmFlow, SwarmResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MockAgentResult:
    def __init__(self, text: str, session_id: str = "sess"):
        self.text = text
        self.session_id = session_id
        self.metadata = {}


class _MockAgent:
    def __init__(self, response: str = "answer"):
        self._response = response

    async def run(self, prompt: str, session_id=None) -> _MockAgentResult:
        return _MockAgentResult(text=self._response)


class _FailingAgent:
    async def run(self, prompt: str, session_id=None) -> _MockAgentResult:
        raise RuntimeError("agent crashed")


# ---------------------------------------------------------------------------
# SwarmResult
# ---------------------------------------------------------------------------


def test_swarm_result_defaults():
    r = SwarmResult(output="hello")
    assert r.strategy == "best_of"
    assert r.candidates == []
    assert r.metadata == {}


# ---------------------------------------------------------------------------
# SwarmFlow construction
# ---------------------------------------------------------------------------


def test_swarm_flow_requires_agents():
    with pytest.raises(SdkError, match="at least one agent"):
        SwarmFlow.create([])


def test_swarm_flow_invalid_strategy_raises():
    agent = _MockAgent()
    with pytest.raises(SdkError, match="Unknown strategy"):
        SwarmFlow.create([agent], strategy="random_pick")


def test_swarm_flow_valid_strategies():
    agent = _MockAgent()
    for strategy in ("best_of", "majority_vote", "first"):
        sf = SwarmFlow.create([agent], strategy=strategy)
        assert sf._strategy == strategy


# ---------------------------------------------------------------------------
# SwarmFlow.run — best_of
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_swarm_run_best_of_returns_result():
    agents = [_MockAgent("short"), _MockAgent("much longer answer here")]
    sf = SwarmFlow.create(agents, strategy="best_of")
    result = await sf.run("Q")
    assert isinstance(result, SwarmResult)
    assert result.strategy == "best_of"
    # best_of selects longest — "much longer answer here"
    assert result.output == "much longer answer here"


@pytest.mark.asyncio
async def test_swarm_run_candidates_populated():
    agents = [_MockAgent("A"), _MockAgent("B"), _MockAgent("C")]
    sf = SwarmFlow.create(agents)
    result = await sf.run("Q")
    assert len(result.candidates) == 3
    assert "A" in result.candidates
    assert "B" in result.candidates
    assert "C" in result.candidates


# ---------------------------------------------------------------------------
# SwarmFlow.run — majority_vote
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_swarm_run_majority_vote():
    agents = [_MockAgent("Paris"), _MockAgent("Paris"), _MockAgent("London")]
    sf = SwarmFlow.create(agents, strategy="majority_vote")
    result = await sf.run("What is the capital of France?")
    assert result.output == "Paris"


# ---------------------------------------------------------------------------
# SwarmFlow.run — first
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_swarm_run_first():
    agents = [_MockAgent("first answer"), _MockAgent("second answer")]
    sf = SwarmFlow.create(agents, strategy="first")
    result = await sf.run("Q")
    assert result.output == "first answer"


# ---------------------------------------------------------------------------
# SwarmFlow.run — failure handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_swarm_all_agents_fail_raises():
    agents = [_FailingAgent(), _FailingAgent()]
    sf = SwarmFlow.create(agents)
    with pytest.raises(SdkError, match="All agents"):
        await sf.run("Q")


@pytest.mark.asyncio
async def test_swarm_partial_failure_succeeds():
    agents = [_FailingAgent(), _MockAgent("good answer")]
    sf = SwarmFlow.create(agents, strategy="first")
    result = await sf.run("Q")
    assert result.output == "good answer"


# ---------------------------------------------------------------------------
# repr
# ---------------------------------------------------------------------------


def test_swarm_flow_repr():
    sf = SwarmFlow.create([_MockAgent()], strategy="majority_vote")
    rep = repr(sf)
    assert "majority_vote" in rep
    assert "1" in rep
