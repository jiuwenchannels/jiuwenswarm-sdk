"""Unit tests for openjiuwen.sdk.eval — evaluation metrics."""

from __future__ import annotations

import pytest

from openjiuwen.sdk.eval import (
    EvalCase,
    EvalResult,
    Evaluator,
    ExactMatchMetric,
    HITTEvaluator,
    HITTResult,
    LLMAsJudgeMetric,
    Metric,
    MetricEvaluator,
)


# ---------------------------------------------------------------------------
# EvalCase tests
# ---------------------------------------------------------------------------


def test_eval_case_defaults():
    case = EvalCase(input="What is 2+2?")
    assert case.expected == ""
    assert case.prediction == ""
    assert case.scores == {}


def test_eval_case_with_prediction():
    case = EvalCase(input="Q", expected="4", prediction="4")
    assert case.prediction == "4"


# ---------------------------------------------------------------------------
# ExactMatchMetric tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_exact_match_pass():
    metric = ExactMatchMetric()
    case = EvalCase(input="2+2?", expected="4", prediction="4")
    score = await metric.score(case)
    assert score == 1.0


@pytest.mark.asyncio
async def test_exact_match_fail():
    metric = ExactMatchMetric()
    case = EvalCase(input="2+2?", expected="4", prediction="five")
    score = await metric.score(case)
    assert score == 0.0


@pytest.mark.asyncio
async def test_exact_match_case_insensitive():
    metric = ExactMatchMetric(case_sensitive=False)
    case = EvalCase(input="Q", expected="Tokyo", prediction="tokyo")
    score = await metric.score(case)
    assert score == 1.0


@pytest.mark.asyncio
async def test_exact_match_case_sensitive_fail():
    metric = ExactMatchMetric(case_sensitive=True)
    case = EvalCase(input="Q", expected="Tokyo", prediction="tokyo")
    score = await metric.score(case)
    assert score == 0.0


@pytest.mark.asyncio
async def test_exact_match_strips_whitespace():
    metric = ExactMatchMetric()
    case = EvalCase(input="Q", expected="  4  ", prediction="4 ")
    score = await metric.score(case)
    assert score == 1.0


# ---------------------------------------------------------------------------
# LLMAsJudgeMetric tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_llm_judge_heuristic_full_match():
    metric = LLMAsJudgeMetric(criteria="Is it correct?")
    case = EvalCase(input="Q", expected="The sky is blue", prediction="The sky is blue")
    score = await metric.score(case)
    assert score == 1.0


@pytest.mark.asyncio
async def test_llm_judge_heuristic_no_overlap():
    metric = LLMAsJudgeMetric()
    case = EvalCase(input="Q", expected="sky blue", prediction="ocean deep")
    score = await metric.score(case)
    assert 0.0 <= score <= 1.0


@pytest.mark.asyncio
async def test_llm_judge_empty_expected():
    metric = LLMAsJudgeMetric()
    case = EvalCase(input="Q", expected="", prediction="")
    score = await metric.score(case)
    assert score == 1.0


# ---------------------------------------------------------------------------
# MetricEvaluator tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_metric_evaluator_batch():
    cases = [
        EvalCase(input="2+2?", expected="4", prediction="4"),
        EvalCase(input="3+3?", expected="6", prediction="7"),
    ]
    evaluator = MetricEvaluator(metrics=[ExactMatchMetric()])
    scored = await evaluator.batch_evaluate(cases)
    assert scored[0].scores["exact_match"] == 1.0
    assert scored[1].scores["exact_match"] == 0.0


@pytest.mark.asyncio
async def test_metric_evaluator_multiple_metrics():
    cases = [EvalCase(input="Q", expected="four", prediction="four")]
    evaluator = MetricEvaluator(metrics=[ExactMatchMetric(), LLMAsJudgeMetric()])
    scored = await evaluator.batch_evaluate(cases)
    assert "exact_match" in scored[0].scores
    assert "llm_judge" in scored[0].scores


@pytest.mark.asyncio
async def test_metric_evaluator_single():
    case = EvalCase(input="Q", expected="yes", prediction="yes")
    evaluator = MetricEvaluator(metrics=[ExactMatchMetric()])
    result = await evaluator.evaluate(case)
    assert result.scores["exact_match"] == 1.0


def test_metric_evaluator_empty_metrics_raises():
    with pytest.raises(ValueError, match="metrics must not be empty"):
        MetricEvaluator(metrics=[])


def test_metric_evaluator_aggregate():
    cases = [
        EvalCase(input="A", expected="x", prediction="x", scores={"exact_match": 1.0}),
        EvalCase(input="B", expected="y", prediction="z", scores={"exact_match": 0.0}),
    ]
    evaluator = MetricEvaluator(metrics=[ExactMatchMetric()])
    result = evaluator.aggregate(cases)
    assert isinstance(result, EvalResult)
    assert result.aggregate["exact_match"] == pytest.approx(0.5)
    assert result.total_cases == 2


# ---------------------------------------------------------------------------
# HITTEvaluator tests
# ---------------------------------------------------------------------------


def test_hitt_evaluator_all_confident():
    hitt = HITTEvaluator(threshold=0.7, metric_name="llm_judge")
    cases = [
        EvalCase(input="A", expected="x", prediction="x", scores={"llm_judge": 0.9}),
        EvalCase(input="B", expected="y", prediction="y", scores={"llm_judge": 0.8}),
    ]
    result_obj = EvalResult(cases=cases)
    hitt_result = hitt.evaluate(result_obj)
    assert isinstance(hitt_result, HITTResult)
    assert hitt_result.review_fraction == 0.0
    assert hitt_result.hitt_score == 1.0


def test_hitt_evaluator_some_review_needed():
    hitt = HITTEvaluator(threshold=0.8, metric_name="llm_judge")
    cases = [
        EvalCase(input="A", expected="x", prediction="x", scores={"llm_judge": 0.9}),
        EvalCase(input="B", expected="y", prediction="z", scores={"llm_judge": 0.5}),
    ]
    result_obj = EvalResult(cases=cases)
    hitt_result = hitt.evaluate(result_obj)
    assert hitt_result.review_count == 1
    assert hitt_result.review_fraction == 0.5


def test_hitt_evaluator_empty_cases():
    hitt = HITTEvaluator()
    hitt_result = hitt.evaluate(EvalResult(cases=[]))
    assert hitt_result.review_fraction == 0.0
    assert hitt_result.review_count == 0


def test_hitt_evaluator_invalid_threshold():
    with pytest.raises(ValueError):
        HITTEvaluator(threshold=1.5)


# Alias check
def test_evaluator_alias():
    assert Evaluator is MetricEvaluator
