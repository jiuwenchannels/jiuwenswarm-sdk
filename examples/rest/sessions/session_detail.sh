#!/usr/bin/env bash
# Session detail operations: rename, switch, history.
# Requires the gateway to be running: jiuwenswarm serve
#   WS:   ws://localhost:19000
#   HTTP: http://localhost:19001

BASE="http://localhost:19001"

# ---------------------------------------------------------------------------
# 1. List sessions so we have an ID to work with
# ---------------------------------------------------------------------------
echo "=== List sessions ==="
SESSION_JSON=$(curl -s "$BASE/v1/sessions")
echo "$SESSION_JSON" | python3 -m json.tool

# Extract the first session ID using Python (portable across macOS / Linux).
SESSION_ID=$(echo "$SESSION_JSON" | python3 -c "
import json, sys
sessions = json.load(sys.stdin).get('sessions', [])
print(sessions[0]['id'] if sessions else '')
")

if [ -z "$SESSION_ID" ]; then
  echo "No sessions found. Creating one first..."
  SESSION_ID=$(curl -s -X POST "$BASE/v1/sessions" \
    -H "Content-Type: application/json" \
    -d '{"title": "Demo session"}' | python3 -c "import json,sys; print(json.load(sys.stdin)['session']['id'])")
fi

echo ""
echo "Working with session: $SESSION_ID"

# ---------------------------------------------------------------------------
# 2. Rename session
# ---------------------------------------------------------------------------
echo ""
echo "=== Rename session ==="
curl -s -X PATCH "$BASE/v1/sessions/$SESSION_ID" \
  -H "Content-Type: application/json" \
  -d "{\"title\": \"Renamed via REST $(date +%H:%M:%S)\"}" \
  | python3 -m json.tool

# ---------------------------------------------------------------------------
# 3. Get session detail
# ---------------------------------------------------------------------------
echo ""
echo "=== Get session detail ==="
curl -s "$BASE/v1/sessions/$SESSION_ID" | python3 -m json.tool

# ---------------------------------------------------------------------------
# 4. Switch active session
#    POST /v1/sessions/{id}/switch tells the gateway which session is active
#    for subsequent requests from this connection.
# ---------------------------------------------------------------------------
echo ""
echo "=== Switch to session ==="
curl -s -X POST "$BASE/v1/sessions/$SESSION_ID/switch" \
  -H "Content-Type: application/json" \
  | python3 -m json.tool

# ---------------------------------------------------------------------------
# 5. Load paginated history (page 1)
# ---------------------------------------------------------------------------
echo ""
echo "=== Session history (page 1) ==="
curl -s "$BASE/v1/sessions/$SESSION_ID/history?page=1" | python3 -m json.tool

# ---------------------------------------------------------------------------
# 6. Load history — page 2 (may be empty if few messages)
# ---------------------------------------------------------------------------
echo ""
echo "=== Session history (page 2) ==="
curl -s "$BASE/v1/sessions/$SESSION_ID/history?page=2" | python3 -m json.tool
