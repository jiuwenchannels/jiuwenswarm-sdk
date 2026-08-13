"""15_multi_rollout.py — run the same prompt N times and pick the best result.

Corresponds to §15 of the usage examples.

Shows:
  - MultiRolloutConfig with n, temperature, concurrency
  - MultiRolloutExecutor.run() returning N results
  - executor.best_of() using an LLMAsJudgeMetric to rank results

Run:
    python examples/15_multi_rollout.py
"""

import asyncio
from openjiuwen.sdk import Agent, ModelConfig
from openjiuwen.sdk.rollout import MultiRolloutConfig, MultiRolloutExecutor


async def main():
    agent = await Agent.create("rollout-agent", model=ModelConfig.from_env())

    rollout_cfg = MultiRolloutConfig(
        n=5,                        # run 5 times
        temperature=0.9,            # high temperature for diversity
        concurrency=3,              # up to 3 runs in parallel
    )

    executor = MultiRolloutExecutor(agent, rollout_cfg)
    results = await executor.run("Write a one-sentence tagline for a cloud storage product.")

    for i, r in enumerate(results):
        print(f"[{i+1}] {r.text}")

    # Pick the highest-scored result (requires an evaluator)
    from openjiuwen.sdk.eval import LLMAsJudgeMetric, EvalCase
    metric = LLMAsJudgeMetric(criteria="Most creative and memorable tagline")
    best = await executor.best_of(results, metric=metric)
    print(f"\nBest: {best.text}")


if __name__ == "__main__":
    asyncio.run(main())
