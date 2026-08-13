#!/usr/bin/env bash
# 07_eval_batch.sh — run an evaluation batch against a registered agent.
#
# Prerequisites:
#   jiuwenswarm serve   (starts the gateway on port 19001 by default)
#   An agent registered under the ID "deep-agent"

curl -X POST http://localhost:19001/v1/eval/batch \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "deep-agent",
    "metrics": ["exact_match", "llm_judge"],
    "cases": [
      {"input": "What is 2 + 2?",    "expected": "4"},
      {"input": "Capital of Japan?", "expected": "Tokyo"}
    ]
  }'

# Expected response:
# {
#   "results": [
#     {
#       "input": "What is 2 + 2?",
#       "prediction": "4",
#       "scores": {"exact_match": 1.0, "llm_judge": 1.0}
#     },
#     {
#       "input": "Capital of Japan?",
#       "prediction": "The capital of Japan is Tokyo.",
#       "scores": {"exact_match": 0.0, "llm_judge": 0.95}
#     }
#   ],
#   "summary": {"exact_match": 0.5, "llm_judge": 0.975}
# }
