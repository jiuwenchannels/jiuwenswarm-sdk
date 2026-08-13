"""10_evaluation.py — evaluate agent output quality with built-in and custom metrics.

Corresponds to §10 of the usage examples.

Shows:
  - EvalCase with input, expected, prediction fields
  - ExactMatchMetric and LLMAsJudgeMetric
  - MetricEvaluator.batch_evaluate()
  - Custom Metric subclass

Run:
    python examples/10_evaluation.py
"""

import asyncio
from openjiuwen.sdk.eval import (
    MetricEvaluator,
    ExactMatchMetric,
    LLMAsJudgeMetric,
    EvalCase,
)


async def main():
    # Define test cases
    cases = [
        EvalCase(input="What is 2 + 2?",       expected="4"),
        EvalCase(input="Capital of Japan?",     expected="Tokyo"),
        EvalCase(input="Who wrote Hamlet?",     expected="Shakespeare"),
    ]

    # Run the agent and collect predictions
    from openjiuwen.sdk import Agent, ModelConfig
    agent = await Agent.create("eval-target", model=ModelConfig.from_env())
    for case in cases:
        result = await agent.run(case.input)
        case.prediction = result.text

    # Score with multiple metrics
    evaluator = MetricEvaluator(
        metrics=[
            ExactMatchMetric(),
            LLMAsJudgeMetric(criteria="Is the answer factually correct?"),
        ]
    )
    scored = await evaluator.batch_evaluate(cases)

    for case in scored:
        print(f"Q: {case.input}")
        print(f"  exact_match={case.scores['exact_match']:.0f}  "
              f"llm_judge={case.scores['llm_judge']:.2f}")


# ---------------------------------------------------------------------------
# Custom metric
# ---------------------------------------------------------------------------

from openjiuwen.sdk.eval import Metric, EvalCase


class LengthMetric(Metric):
    """Scores 1.0 if the prediction is under 50 words, else 0.0."""
    name = "brevity"

    async def score(self, case: EvalCase) -> float:
        return 1.0 if len(case.prediction.split()) <= 50 else 0.0


if __name__ == "__main__":
    asyncio.run(main())
