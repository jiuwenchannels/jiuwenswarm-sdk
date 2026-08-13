"""Batch evaluation REST route.

Route
-----
``POST /v1/eval/batch`` — run a batch of evaluation cases through a metric.

Request::

    {
      "cases": [
        {"input": "What is 2+2?", "expected": "4", "prediction": "4"},
        {"input": "Capital of France?", "expected": "Paris", "prediction": "Lyon"}
      ],
      "metric": "exact_match"
    }

Response::

    {
      "results": [
        {"input": "What is 2+2?", "score": 1.0, "passed": true},
        {"input": "Capital of France?", "score": 0.0, "passed": false}
      ],
      "aggregate": {"mean_score": 0.5, "pass_rate": 0.5, "total": 2}
    }

Supported ``metric`` values: ``"exact_match"``, ``"hitt"``.
For ``"hitt"`` the cases must include a ``"session_id"`` field.
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


# ---------------------------------------------------------------------------
# Request model
# ---------------------------------------------------------------------------


class EvalCase(BaseModel):
    input: str
    expected: str
    prediction: str = ""
    metadata: dict[str, Any] = {}


class BatchEvalRequest(BaseModel):
    cases: list[EvalCase]
    metric: str = "exact_match"


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.post("/eval/batch")
async def batch_eval(body: BatchEvalRequest) -> dict[str, Any]:
    """Run a batch evaluation and return per-case scores and aggregate stats."""
    from openjiuwen.sdk.optimize.eval import EvalCase as SdkEvalCase, ExactMatchMetric, MetricEvaluator

    if body.metric == "exact_match":
        metric = ExactMatchMetric()
    else:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown metric {body.metric!r}. Supported: 'exact_match'",
        )

    sdk_cases = [
        SdkEvalCase(
            input=c.input,
            expected=c.expected,
            prediction=c.prediction,
            metadata=c.metadata,
        )
        for c in body.cases
    ]

    evaluator = MetricEvaluator(metrics=[metric])
    results = await evaluator.evaluate(sdk_cases)

    per_case = []
    for case, result in zip(body.cases, results.per_case):
        per_case.append({
            "input": case.input,
            "score": result.scores.get(metric.name, 0.0),
            "passed": result.passed,
        })

    return {
        "results": per_case,
        "aggregate": {
            "mean_score": results.aggregate.get("mean_score", 0.0),
            "pass_rate": results.aggregate.get("pass_rate", 0.0),
            "total": len(body.cases),
        },
    }
