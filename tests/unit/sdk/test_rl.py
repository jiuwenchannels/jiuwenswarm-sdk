"""Unit tests for openjiuwen.sdk.optimize.rl — OnlineRL, OfflineRL, RLConfig."""

from __future__ import annotations

import json
import pytest

from openjiuwen.sdk.optimize.rl import (
    OfflineRL,
    OnlineRL,
    RLConfig,
    RLStepResult,
    RLTrajectory,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _MockAgentResult:
    def __init__(self, text: str, session_id: str = "sess-1"):
        self.text = text
        self.session_id = session_id
        self.metadata = {}


class _MockAgent:
    def __init__(self, response: str = "the answer"):
        self._response = response

    async def run(self, prompt: str, **kwargs) -> _MockAgentResult:
        return _MockAgentResult(text=self._response)


# ---------------------------------------------------------------------------
# RLConfig tests
# ---------------------------------------------------------------------------


def test_rl_config_defaults():
    cfg = RLConfig()
    assert cfg.algorithm == "ppo"
    assert cfg.learning_rate == 1e-5
    assert cfg.rollouts_per_step == 4
    assert cfg.online is True
    assert cfg.max_trajectory_len == 50


def test_rl_config_valid_algorithms():
    for alg in ("ppo", "dpo", "grpo"):
        cfg = RLConfig(algorithm=alg)
        assert cfg.algorithm == alg


def test_rl_config_invalid_algorithm_raises():
    with pytest.raises(ValueError, match="algorithm"):
        RLConfig(algorithm="reinforce")


def test_rl_config_frozen():
    cfg = RLConfig()
    with pytest.raises((AttributeError, TypeError)):
        cfg.algorithm = "dpo"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# RLTrajectory tests
# ---------------------------------------------------------------------------


def test_rl_trajectory_defaults():
    t = RLTrajectory(prompt="Q", response="A")
    assert t.reward == 0.0
    assert t.num_turns == 1
    assert t.metadata == {}


# ---------------------------------------------------------------------------
# RLStepResult tests
# ---------------------------------------------------------------------------


def test_rl_step_result_defaults():
    r = RLStepResult(text="hello")
    assert r.reward == 0.0
    assert r.session_id is None
    assert r.updated is False


# ---------------------------------------------------------------------------
# OnlineRL tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_online_rl_step_basic():
    agent = _MockAgent("correct answer")
    reward_fn = lambda text: 1.0 if "correct" in text else 0.0
    rl = OnlineRL(agent, RLConfig(algorithm="ppo", reward_fn=reward_fn, rollouts_per_step=10))
    result = await rl.step("What is 2+2?")
    assert result.text == "correct answer"
    assert result.reward == 1.0
    assert result.updated is False  # not enough rollouts yet


@pytest.mark.asyncio
async def test_online_rl_trajectory_accumulates():
    agent = _MockAgent("yes")
    rl = OnlineRL(agent, RLConfig(rollouts_per_step=10))
    await rl.step("Q1")
    await rl.step("Q2")
    trajs = rl.get_trajectories()
    assert len(trajs) == 2
    assert trajs[0].prompt == "Q1"


@pytest.mark.asyncio
async def test_online_rl_clear_trajectories():
    agent = _MockAgent("yes")
    rl = OnlineRL(agent, RLConfig(rollouts_per_step=10))
    await rl.step("Q")
    rl.clear_trajectories()
    assert rl.get_trajectories() == []


@pytest.mark.asyncio
async def test_online_rl_override_reward_fn():
    agent = _MockAgent("some text")
    rl = OnlineRL(agent, RLConfig(reward_fn=lambda t: 0.0))
    result = await rl.step("Q", reward_fn=lambda t: 0.99)
    assert result.reward == pytest.approx(0.99)


@pytest.mark.asyncio
async def test_online_rl_no_reward_fn_gives_zero():
    agent = _MockAgent("hello")
    rl = OnlineRL(agent, RLConfig(reward_fn=None))
    result = await rl.step("Q")
    assert result.reward == 0.0


@pytest.mark.asyncio
async def test_online_rl_update_triggered_after_rollouts():
    agent = _MockAgent("ok")
    rl = OnlineRL(agent, RLConfig(online=True, rollouts_per_step=3))
    results = [await rl.step("Q") for _ in range(3)]
    # The 3rd step should have triggered an update
    assert results[-1].updated is True


def test_online_rl_repr():
    agent = _MockAgent()
    rl = OnlineRL(agent, RLConfig(algorithm="dpo"))
    rep = repr(rl)
    assert "dpo" in rep


# ---------------------------------------------------------------------------
# OfflineRL tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_offline_rl_step_basic():
    agent = _MockAgent("the output")
    rl = OfflineRL(agent, RLConfig(online=False))
    result = await rl.step("Q")
    assert result.text == "the output"
    assert result.updated is False


@pytest.mark.asyncio
async def test_offline_rl_export_trajectories(tmp_path):
    agent = _MockAgent("resp")
    reward_fn = lambda t: 0.5
    rl = OfflineRL(agent, RLConfig(online=False, reward_fn=reward_fn))
    await rl.step("prompt1")
    await rl.step("prompt2")

    out_path = str(tmp_path / "trajectories.jsonl")
    rl.export_trajectories(out_path)

    lines = open(out_path).readlines()
    assert len(lines) == 2
    first = json.loads(lines[0])
    assert first["prompt"] == "prompt1"
    assert first["reward"] == pytest.approx(0.5)


@pytest.mark.asyncio
async def test_offline_rl_get_trajectories():
    agent = _MockAgent("answer")
    rl = OfflineRL(agent, RLConfig(online=False))
    await rl.step("A")
    await rl.step("B")
    trajs = rl.get_trajectories()
    assert len(trajs) == 2
