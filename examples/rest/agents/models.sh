#!/usr/bin/env bash
# LLM model discovery and switching via REST.
# Requires the gateway to be running: jiuwenswarm serve
#   HTTP: http://localhost:19001

BASE="http://localhost:19001"

# ---------------------------------------------------------------------------
# 1. List available models
#    Returns all LLM backends the gateway knows about, including which is
#    currently active.
# ---------------------------------------------------------------------------
echo "=== List available models ==="
MODELS_JSON=$(curl -s "$BASE/v1/models")
echo "$MODELS_JSON" | python3 -m json.tool

# Extract the active model ID.
ACTIVE=$(echo "$MODELS_JSON" | python3 -c "
import json, sys
data = json.load(sys.stdin)
models = data.get('models', [])
active = next((m for m in models if m.get('active')), None)
print(active['id'] if active else (models[0]['id'] if models else ''))
")
echo ""
echo "Active model: $ACTIVE"

# ---------------------------------------------------------------------------
# 2. Switch to a different model
#    PUT /v1/models/active with {"model_id": "..."} swaps the active backend.
# ---------------------------------------------------------------------------
echo ""
echo "=== Switch active model ==="
TARGET_MODEL="${1:-gpt-4o-mini}"   # Accept model ID as first argument.
curl -s -X PUT "$BASE/v1/models/active" \
  -H "Content-Type: application/json" \
  -d "{\"model_id\": \"$TARGET_MODEL\"}" \
  | python3 -m json.tool

# ---------------------------------------------------------------------------
# 3. Confirm the switch
# ---------------------------------------------------------------------------
echo ""
echo "=== Confirm active model after switch ==="
curl -s "$BASE/v1/models" | python3 -c "
import json, sys
data = json.load(sys.stdin)
for m in data.get('models', []):
    flag = ' <-- ACTIVE' if m.get('active') else ''
    print(f\"  {m['id']:40s} {m.get('provider',''):20s}{flag}\")
"

# ---------------------------------------------------------------------------
# 4. Send a quick chat to verify the new model responds
# ---------------------------------------------------------------------------
echo ""
echo "=== Quick chat with new model ($TARGET_MODEL) ==="
curl -s -X POST "$BASE/v1/chat" \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"Reply with the word PONG only.\", \"stream\": false}" \
  | python3 -m json.tool
