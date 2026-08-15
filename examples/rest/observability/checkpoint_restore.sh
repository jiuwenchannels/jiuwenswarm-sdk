#!/usr/bin/env bash
# 09_checkpoint_restore.sh — save agent state to a checkpoint and restore it.
#
# Prerequisites:
#   jiuwenswarm serve   (starts the gateway on port 19001 by default)
#   SESSION_ID environment variable, or edit the value below.

SESSION_ID="${SESSION_ID:-sess_abc123}"
BASE=http://localhost:19001/v1

# Save agent state — returns a checkpoint ID
echo "=== Create checkpoint ==="
CHECKPOINT=$(curl -s -X POST "$BASE/agents/deep-agent/checkpoint" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\"}")
echo "$CHECKPOINT"

CHECKPOINT_ID=$(echo "$CHECKPOINT" | python3 -c "import sys,json; print(json.load(sys.stdin)['checkpoint_id'])")
echo "Checkpoint ID: $CHECKPOINT_ID"

echo

# List available checkpoints
echo "=== List checkpoints ==="
curl "$BASE/checkpoints"

echo

# Restore from the checkpoint — creates a new session pre-loaded with saved state
echo "=== Restore checkpoint ==="
RESTORED=$(curl -s -X POST "$BASE/checkpoints/$CHECKPOINT_ID/restore")
echo "$RESTORED"

RESTORED_SESSION=$(echo "$RESTORED" | python3 -c "import sys,json; print(json.load(sys.stdin)['session_id'])")
echo "Restored session: $RESTORED_SESSION"

echo

# Continue the restored session
echo "=== Continue restored session ==="
curl -X POST "$BASE/sessions/$RESTORED_SESSION/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "Continue from where we left off."}'
