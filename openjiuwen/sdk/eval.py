"""SDK evaluation module — score agent output quality with built-in and custom metrics.

Quick start::

    from openjiuwen.sdk.eval import MetricEvaluator, ExactMatchMetric, EvalCase

    cases = [EvalCase(input="2+2?", expected="4")]
    # populate case.prediction from your agent
    evaluator = MetricEvaluator(metrics=[ExactMatchMetric()])
    scored = await evaluator.batch_evaluate(cases)
    print(scored[0].scores)  # {"exact_match": 1.0}
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# EvalCase
# ---------------------------------------------------------------------------


@dataclass
class EvalCase:
    """A single evaluation test case.

    Attributes:
        input:      The prompt / question given to the agent.
        expected:   The expected (gold) answer.
        prediction: The agent's actual answer (filled in after agent.run()).
        scores:     Metric scores populated by :meth:`MetricEvaluator.batch_evaluate`.
        metadata:   Optional extra fields.
    """

    input: str
    expected: str = ""
    prediction: str = ""
    scores: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# EvalResult
# ---------------------------------------------------------------------------


@dataclass
class EvalResult:
    """Aggregate result of an evaluation run.

    Attributes:
        cases:          All evaluated :class:`EvalCase` objects.
        aggregate:      Mean score per metric across all cases.
        total_cases:    Number of cases evaluated.
    """

    cases: list[EvalCase] = field(default_factory=list)
    aggregate: dict[str, float] = field(default_factory=dict)
    total_cases: int = 0

    def __post_init__(self) -> None:
        if not self.total_cases:
            self.total_cases = len(self.cases)


# ---------------------------------------------------------------------------
# Metric base class
# ---------------------------------------------------------------------------


class Metric(abc.ABC):
    """Abstract base class for evaluation metrics.

    Subclass this to create custom metrics::

        class BrevityMetric(Metric):
            name = "brevity"

            async def score(self, case: EvalCase) -> float:
                return 1.0 if len(case.prediction.split()) <= 50 else 0.0
    """

    name: str = "metric"

    @abc.abstractmethod
    async def score(self, case: EvalCase) -> float:
        """Return a score in [0, 1] for *case*.

        Args:
            case: The evaluation case (``case.prediction`` holds the agent output).

        Returns:
            A float in [0, 1] where 1 is perfect.
        """


# ---------------------------------------------------------------------------
# Built-in metrics
# ---------------------------------------------------------------------------


class ExactMatchMetric(Metric):
    """Returns 1.0 if ``prediction.strip() == expected.strip()``, else 0.0.

    Case-insensitive by default.

    Example::

        metric = ExactMatchMetric()
        score = await metric.score(EvalCase(input="2+2?", expected="4", prediction="4"))
        assert score == 1.0
    """

    name = "exact_match"

    def __init__(self, case_sensitive: bool = False) -> None:
        self._case_sensitive = case_sensitive

    async def score(self, case: EvalCase) -> float:
        pred = case.prediction.strip()
        exp = case.expected.strip()
        if not self._case_sensitive:
            pred = pred.lower()
            exp = exp.lower()
        return 1.0 if pred == exp else 0.0


class LLMAsJudgeMetric(Metric):
    """Uses an LLM to judge the quality of a prediction against the expected answer.

    The LLM is prompted with the *criteria* and returns a score in [0, 1].

    When the runtime is not available, this metric falls back to a simple
    substring-match heuristic so tests do not require a live LLM.

    Example::

        metric = LLMAsJudgeMetric(criteria="Is the answer factually correct?")
        score = await metric.score(case)
    """

    name = "llm_judge"

    def __init__(
        self,
        criteria: str = "Is the answer correct and helpful?",
        model: str = "gpt-4o",
        llm_client: Any = None,
    ) -> None:
        self._criteria = criteria
        self._model = model
        self._llm_client = llm_client

    async def score(self, case: EvalCase) -> float:
        if self._llm_client is not None:
            return await self._judge_with_llm(case)
        # Heuristic fallback: partial credit based on word overlap
        pred_words = set(case.prediction.lower().split())
        exp_words = set(case.expected.lower().split())
        if not exp_words:
            return 1.0 if not pred_words else 0.5
        overlap = pred_words & exp_words
        return min(1.0, len(overlap) / len(exp_words))

    async def _judge_with_llm(self, case: EvalCase) -> float:
        prompt = (
            f"Criteria: {self._criteria}\n"
            f"Question: {case.input}\n"
            f"Expected: {case.expected}\n"
            f"Prediction: {case.prediction}\n"
            "Score from 0.0 (completely wrong) to 1.0 (perfect). "
            "Reply with only the numeric score."
        )
        try:
            response = await self._llm_client.complete(prompt)
            text = getattr(response, "text", str(response)).strip()
            return float(text)
        except Exception:  # noqa: BLE001
            return 0.5


# ---------------------------------------------------------------------------
# MetricEvaluator (roadmap: Evaluator)
# ---------------------------------------------------------------------------


class MetricEvaluator:
    """Runs one or more :class:`Metric` instances against a list of cases.

    Example::

        evaluator = MetricEvaluator(metrics=[ExactMatchMetric(), LLMAsJudgeMetric(...)])
        scored = await evaluator.batch_evaluate(cases)
    """

    def __init__(self, metrics: list[Metric]) -> None:
        if not metrics:
            raise ValueError("metrics must not be empty")
        self._metrics = metrics

    async def batch_evaluate(self, cases: list[EvalCase]) -> list[EvalCase]:
        """Score all *cases* with every registered metric.

        Populates ``case.scores`` in-place for each case and returns the list.

        Args:
            cases: List of :class:`EvalCase` objects with ``prediction`` filled in.

        Returns:
            The same list with ``case.scores`` populated.
        """
        for case in cases:
            for metric in self._metrics:
                case.scores[metric.name] = await metric.score(case)
        return cases

    async def evaluate(self, case: EvalCase) -> EvalCase:
        """Score a single *case*.  Returns *case* with ``scores`` populated."""
        return (await self.batch_evaluate([case]))[0]

    def aggregate(self, cases: list[EvalCase]) -> EvalResult:
        """Compute per-metric mean scores across all *cases*.

        Args:
            cases: Scored cases (output of :meth:`batch_evaluate`).

        Returns:
            :class:`EvalResult` with ``aggregate`` means.
        """
        agg: dict[str, list[float]] = {}
        for case in cases:
            for metric_name, score in case.scores.items():
                agg.setdefault(metric_name, []).append(score)
        means = {k: sum(v) / len(v) for k, v in agg.items() if v}
        return EvalResult(cases=cases, aggregate=means, total_cases=len(cases))


# Alias to match roadmap name
Evaluator = MetricEvaluator


# ---------------------------------------------------------------------------
# HITTEvaluator — Human-in-the-Team evaluation estimator
# ---------------------------------------------------------------------------


class HITTEvaluator:
    """Wraps an :class:`EvalResult` to estimate human-in-the-loop effort.

    The ``hitt_score`` represents the fraction of cases that a human would
    need to review, based on a configurable confidence threshold.

    Example::

        hitt = HITTEvaluator(threshold=0.8)
        score = hitt.evaluate(eval_result)
        print(f"Human review needed for {score.review_fraction:.0%} of cases")
    """

    def __init__(
        self,
        threshold: float = 0.8,
        metric_name: str = "llm_judge",
    ) -> None:
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("threshold must be in [0, 1]")
        self._threshold = threshold
        self._metric_name = metric_name

    def evaluate(self, result: EvalResult) -> "HITTResult":
        """Estimate human effort required for *result*.

        Args:
            result: :class:`EvalResult` from :meth:`MetricEvaluator.aggregate`.

        Returns:
            :class:`HITTResult` with ``review_fraction`` and ``hitt_score``.
        """
        if not result.cases:
            return HITTResult(review_fraction=0.0, hitt_score=1.0, review_count=0)

        review_cases = [
            c
            for c in result.cases
            if c.scores.get(self._metric_name, 0.0) < self._threshold
        ]
        review_fraction = len(review_cases) / len(result.cases)
        hitt_score = 1.0 - review_fraction
        return HITTResult(
            review_fraction=review_fraction,
            hitt_score=hitt_score,
            review_count=len(review_cases),
        )


@dataclass(frozen=True)
class HITTResult:
    """Result of a :class:`HITTEvaluator` pass.

    Attributes:
        review_fraction: Fraction of cases needing human review (0–1).
        hitt_score:      Overall automation confidence (1 − review_fraction).
        review_count:    Absolute number of cases needing review.
    """

    review_fraction: float
    hitt_score: float
    review_count: int
