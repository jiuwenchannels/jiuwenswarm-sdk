"""Tests for POST /v1/eval/batch."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers — stub EvalResult returned by the mock evaluator
# ---------------------------------------------------------------------------


@dataclass
class _FakePerCase:
    scores: dict = field(default_factory=lambda: {"exact_match": 1.0})
    passed: bool = True


@dataclass
class _FakeEvalResult:
    per_case: list = field(default_factory=list)
    aggregate: dict = field(default_factory=lambda: {"mean_score": 1.0, "pass_rate": 1.0})


def _make_eval_result(n: int, score: float = 1.0, passed: bool = True) -> "_FakeEvalResult":
    return _FakeEvalResult(
        per_case=[_FakePerCase(scores={"exact_match": score}, passed=passed) for _ in range(n)],
        aggregate={"mean_score": score, "pass_rate": float(passed)},
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_batch_eval_exact_match(client, monkeypatch):
    async def _fake_evaluate(cases):
        return _make_eval_result(len(cases), score=1.0, passed=True)

    mock_evaluator = MagicMock()
    mock_evaluator.evaluate = _fake_evaluate

    with patch(
        "openjiuwen.sdk.optimize.eval.MetricEvaluator",
        return_value=mock_evaluator,
    ):
        resp = client.post(
            "/v1/eval/batch",
            json={
                "metric": "exact_match",
                "cases": [
                    {"input": "2+2", "expected": "4", "prediction": "4"},
                    {"input": "capital of France", "expected": "Paris", "prediction": "Paris"},
                ],
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) == 2
    assert data["aggregate"]["total"] == 2
    assert "mean_score" in data["aggregate"]


def test_batch_eval_unknown_metric_400(client):
    resp = client.post(
        "/v1/eval/batch",
        json={
            "metric": "rouge",
            "cases": [{"input": "x", "expected": "y", "prediction": "z"}],
        },
    )
    assert resp.status_code == 400
    assert "Unknown metric" in resp.json()["detail"]


def test_batch_eval_empty_cases(client, monkeypatch):
    async def _fake_evaluate(cases):
        return _make_eval_result(0)

    mock_evaluator = MagicMock()
    mock_evaluator.evaluate = _fake_evaluate

    with patch(
        "openjiuwen.sdk.optimize.eval.MetricEvaluator",
        return_value=mock_evaluator,
    ):
        resp = client.post(
            "/v1/eval/batch",
            json={"metric": "exact_match", "cases": []},
        )

    assert resp.status_code == 200
    assert resp.json()["aggregate"]["total"] == 0
