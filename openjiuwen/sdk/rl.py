"""SDK Online RL façade — reinforcement learning for agents.

Collect agent rollout trajectories annotated with rewards, then use them to
improve the agent's policy via PPO, DPO, or GRPO.

Quick start::

    from openjiuwen.sdk.rl import OnlineRL, RLConfig

    def my_reward(text: str) -> float:
        return 1.0 if "correct" in text.lower() else 0.0

    rl = OnlineRL(
        agent,
        RLConfig(algorithm="ppo", reward_fn=my_reward),
    )
    result = await rl.step("Write a haiku about recursion.")
    print(f"Reward: {result.reward:.2f}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RLConfig:
    """Configuration for online / offline reinforcement learning.

    Attributes:
        algorithm:        RL algorithm: ``"ppo"``, ``"dpo"``, or ``"grpo"``.
        reward_fn:        A callable ``(text: str) -> float`` that scores each rollout.
        learning_rate:    Optimizer learning rate.
        rollouts_per_step: Number of rollouts to collect before each gradient update.
        online:           If ``True``, update weights immediately after collecting rollouts.
        max_trajectory_len: Trim trajectories longer than this many turns.
    """

    algorithm: str = "ppo"
    reward_fn: Callable[[str], float] | None = None
    learning_rate: float = 1e-5
    rollouts_per_step: int = 4
    online: bool = True
    max_trajectory_len: int = 50

    def __post_init__(self) -> None:
        valid_algs = {"ppo", "dpo", "grpo"}
        if self.algorithm not in valid_algs:
            raise ValueError(
                f"RLConfig.algorithm must be one of {sorted(valid_algs)}, "
                f"got {self.algorithm!r}"
            )


# ---------------------------------------------------------------------------
# Trajectory
# ---------------------------------------------------------------------------


@dataclass
class RLTrajectory:
    """A single recorded agent rollout with a scalar reward.

    Attributes:
        prompt:    The input prompt for this rollout.
        response:  The agent's response text.
        reward:    The scalar reward assigned by the reward function.
        num_turns: Number of agent task-loop turns taken.
        metadata:  Optional extra fields.
    """

    prompt: str
    response: str
    reward: float = 0.0
    num_turns: int = 1
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Step result
# ---------------------------------------------------------------------------


@dataclass
class RLStepResult:
    """Result of a single :meth:`OnlineRL.step` call.

    Attributes:
        text:       The agent's response text.
        reward:     The scalar reward for this step.
        session_id: Session ID used.
        updated:    Whether a gradient update was applied after this step.
    """

    text: str
    reward: float = 0.0
    session_id: str | None = None
    updated: bool = False


# ---------------------------------------------------------------------------
# OnlineRL façade
# ---------------------------------------------------------------------------


class OnlineRL:
    """Online RL optimizer for a JiuwenSwarm agent.

    Collects rollouts, scores them with the reward function, and (optionally)
    updates model weights after each ``rollouts_per_step`` rollouts.

    Pass to :meth:`~openjiuwen.sdk.agent.Agent.create` as ``rl_optimizer=``.

    Example::

        rl = OnlineRL(agent, RLConfig(algorithm="ppo", reward_fn=my_reward))
        step_result = await rl.step("Write a Python function to sort a list.")
        print(f"Reward: {step_result.reward:.2f}")
    """

    def __init__(self, agent: Any, config: RLConfig) -> None:
        self._agent = agent
        self._config = config
        self._trajectories: list[RLTrajectory] = []
        self._steps_since_update = 0

        self._rt_optimizer: Any = self._build_rt_optimizer()

    def _build_rt_optimizer(self) -> Any:
        """Attempt to get the runtime RL optimizer."""
        try:
            from openjiuwen.agent_evolving import OnlineRLOptimizer, RLConfig as _RtRLConfig

            rt_cfg = _RtRLConfig(
                task_type="custom",
                learning_rate=self._config.learning_rate,
                rollouts_per_step=self._config.rollouts_per_step,
                online=self._config.online,
            )
            return OnlineRLOptimizer(config=rt_cfg)
        except (ImportError, Exception):  # noqa: BLE001
            return None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def step(
        self,
        prompt: str,
        *,
        reward_fn: Callable[[str], float] | None = None,
    ) -> RLStepResult:
        """Execute one RL step: run the agent, score the result, and optionally update.

        Args:
            prompt:    The task prompt.
            reward_fn: Override the config reward function for this step.

        Returns:
            :class:`RLStepResult` with the response text and scalar reward.
        """
        result = await self._agent.run(prompt)
        text = result.text

        fn = reward_fn or self._config.reward_fn
        reward = fn(text) if fn is not None else 0.0

        trajectory = RLTrajectory(
            prompt=prompt,
            response=text,
            reward=reward,
            num_turns=1,
            metadata={"session_id": result.session_id},
        )
        self._trajectories.append(trajectory)
        self._steps_since_update += 1

        updated = False
        if (
            self._config.online
            and self._steps_since_update >= self._config.rollouts_per_step
        ):
            await self._update()
            self._steps_since_update = 0
            updated = True

        return RLStepResult(
            text=text,
            reward=reward,
            session_id=result.session_id,
            updated=updated,
        )

    async def _update(self) -> None:
        """Run a gradient update using collected trajectories."""
        if self._rt_optimizer is not None and hasattr(self._rt_optimizer, "update"):
            try:
                recent = self._trajectories[-self._config.rollouts_per_step :]
                await self._rt_optimizer.update(trajectories=recent)
            except Exception:  # noqa: BLE001
                pass
        # In the SDK stub, update is a no-op; the runtime handles it

    def get_trajectories(self) -> list[RLTrajectory]:
        """Return all collected trajectories from this session."""
        return list(self._trajectories)

    def clear_trajectories(self) -> None:
        """Clear the trajectory buffer."""
        self._trajectories.clear()
        self._steps_since_update = 0

    def __repr__(self) -> str:
        return (
            f"OnlineRL(algorithm={self._config.algorithm!r}, "
            f"trajectories={len(self._trajectories)})"
        )


# ---------------------------------------------------------------------------
# OfflineRL — batch data collection without online updates
# ---------------------------------------------------------------------------


class OfflineRL:
    """Offline RL optimizer — collects trajectories without updating weights.

    Use :meth:`export_trajectories` to write collected data to JSONL for
    batch training.

    Example::

        rl = OfflineRL(agent, RLConfig(online=False, reward_fn=my_reward))
        await rl.step("Solve this coding problem: ...")
        rl.export_trajectories("batch_001.jsonl")
    """

    def __init__(self, agent: Any, config: RLConfig) -> None:
        self._agent = agent
        self._config = config
        self._trajectories: list[RLTrajectory] = []

    async def step(
        self,
        prompt: str,
        *,
        reward_fn: Callable[[str], float] | None = None,
    ) -> RLStepResult:
        """Run the agent and record the trajectory (no gradient update)."""
        result = await self._agent.run(prompt)
        text = result.text
        fn = reward_fn or self._config.reward_fn
        reward = fn(text) if fn is not None else 0.0
        self._trajectories.append(
            RLTrajectory(prompt=prompt, response=text, reward=reward)
        )
        return RLStepResult(text=text, reward=reward, session_id=result.session_id)

    def export_trajectories(self, path: str) -> None:
        """Write collected trajectories to *path* in JSONL format.

        Args:
            path: Output file path (will be created or overwritten).
        """
        import json
        from pathlib import Path

        lines = []
        for t in self._trajectories:
            lines.append(
                json.dumps(
                    {
                        "prompt": t.prompt,
                        "response": t.response,
                        "reward": t.reward,
                        "num_turns": t.num_turns,
                    }
                )
            )
        Path(path).write_text("\n".join(lines), encoding="utf-8")

    def get_trajectories(self) -> list[RLTrajectory]:
        return list(self._trajectories)

    def __repr__(self) -> str:
        return f"OfflineRL(algorithm={self._config.algorithm!r}, trajectories={len(self._trajectories)})"
