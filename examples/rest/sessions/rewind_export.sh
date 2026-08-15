#!/usr/bin/env bash
# Rewind a conversation and export a session via REST.
# Requires the gateway to be running: jiuwenswarm serve
#   HTTP: http://localhost:19001

BASE="http://localhost:19001"

# ---------------------------------------------------------------------------
# 1. Resolve a session to work with
# ---------------------------------------------------------------------------
SESSION_JSON=$(curl -s "$BASE/v1/sessions")
SESSION_ID=$(echo "$SESSION_JSON" | python3 -c "
import json, sys
s = json.load(sys.stdin).get('sessions', [])
print(s[0]['id'] if s else '')
")

if [ -z "$SESSION_ID" ]; then
  echo "No sessions found. Creating one..."
  SESSION_ID=$(curl -s -X POST "$BASE/v1/sessions" \
    -H "Content-Type: application/json" \
    -d '{"title":"Rewind demo"}' \
    | python3 -c "import json,sys; print(json.load(sys.stdin)['session']['id'])")
  # Populate with a few turns
  for MSG in "What is the capital of France?" "And of Germany?" "And of Japan?"; do
    curl -s -X POST "$BASE/v1/chat" \
      -H "Content-Type: application/json" \
      -d "{\"message\": \"$MSG\", \"session_id\": \"$SESSION_ID\", \"stream\": false}" > /dev/null
  done
fi

echo "Session: $SESSION_ID"

# ---------------------------------------------------------------------------
# 2. List rewindable messages
#    GET /v1/sessions/{id}/rewindable returns message IDs the server will
#    accept as rewind targets.
# ---------------------------------------------------------------------------
echo ""
echo "=== Rewindable messages ==="
REWINDABLE=$(curl -s "$BASE/v1/sessions/$SESSION_ID/rewindable")
echo "$REWINDABLE" | python3 -m json.tool

# Extract the first rewindable message ID (if any).
REWIND_TARGET=$(echo "$REWINDABLE" | python3 -c "
import json, sys
msgs = json.load(sys.stdin).get('message_ids', [])
print(msgs[0] if msgs else '')
")

# ---------------------------------------------------------------------------
# 3. Rewind to last user turn (no message_id = server picks the last turn)
# ---------------------------------------------------------------------------
echo ""
echo "=== Rewind to last user turn ==="
curl -s -X POST "$BASE/v1/sessions/$SESSION_ID/rewind" \
  -H "Content-Type: application/json" \
  -d '{}' \
  | python3 -m json.tool

# ---------------------------------------------------------------------------
# 4. Rewind to a specific message (if available)
# ---------------------------------------------------------------------------
if [ -n "$REWIND_TARGET" ]; then
  echo ""
  echo "=== Rewind to specific message: $REWIND_TARGET ==="
  curl -s -X POST "$BASE/v1/sessions/$SESSION_ID/rewind" \
    -H "Content-Type: application/json" \
    -d "{\"message_id\": \"$REWIND_TARGET\"}" \
    | python3 -m json.tool
fi

# ---------------------------------------------------------------------------
# 5. Export session as Markdown
# ---------------------------------------------------------------------------
echo ""
echo "=== Export as Markdown ==="
EXPORT=$(curl -s "$BASE/v1/sessions/$SESSION_ID/export?format=markdown")
echo "$EXPORT" | python3 -c "
import json, sys, base64
d = json.load(sys.stdin)
if d.get('url'):
    print('  Download URL:', d['url'])
elif d.get('data'):
    text = base64.b64decode(d['data']).decode()
    print('  Inline export (first 400 chars):')
    print(text[:400])
else:
    print('  (no export data)')
"

# ---------------------------------------------------------------------------
# 6. Export session as JSON
# ---------------------------------------------------------------------------
echo ""
echo "=== Export as JSON ==="
curl -s "$BASE/v1/sessions/$SESSION_ID/export?format=json" | python3 -c "
import json, sys, base64
d = json.load(sys.stdin)
if d.get('url'):
    print('  JSON download URL:', d['url'])
elif d.get('data'):
    obj = json.loads(base64.b64decode(d['data']))
    print('  Messages in export:', len(obj.get('messages', [])))
else:
    print('  (no export data)')
"

# ---------------------------------------------------------------------------
# 7. Gateway metrics
# ---------------------------------------------------------------------------
echo ""
echo "=== Gateway metrics ==="
curl -s "$BASE/v1/metrics" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f\"  requests_total  : {d.get('requests_total', 'n/a')}\")
print(f\"  tokens_total    : {d.get('tokens_total', 'n/a')}\")
print(f\"  active_sessions : {d.get('active_sessions', 'n/a')}\")
print(f\"  uptime_s        : {d.get('uptime_s', 'n/a')}\")
" 2>/dev/null || echo "  (metrics endpoint not available)"
