#!/usr/bin/env bash
# 02_sessions.sh — create, list, inspect, and delete sessions via the REST API.
#
# Prerequisites:
#   jiuwenswarm serve   (starts the gateway on port 19001 by default)

BASE=http://localhost:19001/v1

# List all sessions
echo "=== List sessions ==="
curl "$BASE/sessions"

echo

# Create a session
echo "=== Create session ==="
SESSION=$(curl -s -X POST "$BASE/sessions" \
  -H "Content-Type: application/json" \
  -d '{"title": "API test", "mode": "default"}')
echo "$SESSION"

SESSION_ID=$(echo "$SESSION" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")
echo "Created session: $SESSION_ID"

echo

# Get a session (with message history)
echo "=== Get session ==="
curl "$BASE/sessions/$SESSION_ID"

echo

# Delete the session
echo "=== Delete session ==="
curl -X DELETE "$BASE/sessions/$SESSION_ID"
