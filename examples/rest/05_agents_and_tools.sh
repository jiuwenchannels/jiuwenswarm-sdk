#!/usr/bin/env bash
# 05_agents_and_tools.sh — list agents, run an agent, and list registered tools.
#
# Prerequisites:
#   jiuwenswarm serve   (starts the gateway on port 19001 by default)

BASE=http://localhost:19001/v1

# List registered agents
echo "=== List agents ==="
curl "$BASE/agents"

echo

# Run an agent (blocking)
echo "=== Run agent ==="
curl -X POST "$BASE/agents/support-bot/run" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "How do I reset my password?"}'

echo

# List registered tools
echo "=== List tools ==="
curl "$BASE/tools"
