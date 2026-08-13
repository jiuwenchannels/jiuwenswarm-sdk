#!/usr/bin/env bash
# 03_blocking_chat.sh — send a message and wait for the full agent response.
#
# Prerequisites:
#   jiuwenswarm serve   (starts the gateway on port 19001 by default)
#   SESSION_ID environment variable, or edit the value below.
#
# Expected response:
#   { "response": "A REST API ...", "session_id": "sess_abc123" }

SESSION_ID="${SESSION_ID:-sess_abc123}"

curl -X POST "http://localhost:19001/v1/sessions/$SESSION_ID/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is a REST API?"}'
