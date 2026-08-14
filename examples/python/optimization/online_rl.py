"""28_online_rl.py — online reinforcement learning and trajectory collection.

Corresponds to §28 of the usage examples.

Shows:
  - RolloutWithReward and a custom reward function
  - RewardRegistry.register() to name the reward function
  - RLConfig: task_type, reward_function, learning_rate, rollouts_per_step, online
  - OnlineRLOptimizer — updates model weights as trajectories arrive
  - Agent.create(rl_optimizer=optimizer) for automatic trajectory collection
  - optimizer.get_trajectories() to inspect collected data
  - OfflineRLOptimizer for batch training data export

Run:
    python examples/28_online_rl.py
"""

import asyncio
from openjiuwen.sdk import Agent, ModelConfig
from openjiuwen.agent_evolving import OnlineRLOptimizer, RLConfig
from openjiuwen.agent_evolving.agent_rl import (
    RLTask,
    RolloutWithReward,
    RewardRegistry,
)


# Define a reward function — returns a float in [0, 1]
def code_quality_reward(rollout: RolloutWithReward) -> float:
    """Reward based on whether the agent's code passes tests."""
    if "all tests passed" in rollout.outcome.lower():
        return 1.0
    elif "test failed" in rollout.outcome.lower():
        return 0.1
    return 0.5


async def online_rl_example():
    model_cfg = ModelConfig.from_env()

    # Register the reward function
    reward_registry = RewardRegistry()
    reward_registry.register("code_quality", code_quality_reward)

    rl_config = RLConfig(
        task_type="code_generation",
        reward_function="code_quality",
        learning_rate=1e-5,
        rollouts_per_step=4,          # collect 4 rollouts before each update
        online=True,                   # update in real-time as trajectories arrive
    )

    optimizer = OnlineRLOptimizer(
        config=rl_config,
        reward_registry=reward_registry,
    )

    # Create agent with RL optimizer attached — trajectories are collected automatically
    agent = await Agent.create(
        "rl-agent",
        model=model_cfg,
        rl_optimizer=optimizer,
    )

    # Run tasks; optimizer updates weights in the background
    tasks = [
        "Implement a binary search function in Python with tests.",
        "Write a function to flatten a nested list.",
        "Implement merge sort and verify it sorts correctly.",
    ]
    for task in tasks:
        result = await agent.run(task)
        print(f"[task] {task[:50]}...\n[result] {result.text[:200]}\n")

    # Inspect collected trajectories
    trajectories = optimizer.get_trajectories()
    print(f"\nCollected {len(trajectories)} trajectories this session.")
    for t in trajectories[:2]:
        print(f"  reward={t.reward:.2f} | turns={t.num_turns}")


async def offline_rl_example():
    """Collect trajectories without online updates for batch training."""
    from openjiuwen.agent_evolving import OfflineRLOptimizer

    reward_registry = RewardRegistry()
    reward_registry.register("code_quality", code_quality_reward)

    rl_config = RLConfig(
        task_type="code_generation",
        reward_function="code_quality",
        online=False,
    )

    offline = OfflineRLOptimizer(config=rl_config, reward_registry=reward_registry)
    agent = await Agent.create(
        "data-collection-agent",
        model=ModelConfig.from_env(),
        rl_optimizer=offline,
    )

    tasks = [
        "Implement a stack using a Python list.",
        "Write a recursive Fibonacci function.",
    ]
    for task in tasks:
        await agent.run(task)

    # Export for offline training
    offline.export_trajectories("trajectories_batch_001.jsonl")
    print("Trajectories exported to trajectories_batch_001.jsonl")


async def main():
    await online_rl_example()


if __name__ == "__main__":
    asyncio.run(main())
