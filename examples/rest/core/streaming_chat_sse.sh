#!/usr/bin/env bash
# 04_streaming_chat_sse.sh — stream the agent response via Server-Sent Events.
#
# Prerequisites:
#   jiuwenswarm serve   (starts the gateway on port 19001 by default)
#   SESSION_ID environment variable, or edit the value below.
#
# Each SSE frame looks like:
#   event: token
#   data: {"text": "The"}
#
#   event: done
#   data: {"session_id": "sess_abc123"}

SESSION_ID="${SESSION_ID:-sess_abc123}"

# -N disables output buffering so tokens appear as they arrive
curl -N -X POST "http://localhost:19001/v1/sessions/$SESSION_ID/chat/stream" \
  -H "Content-Type: application/json" \
  -d '{"message": "Write a short poem about the sea."}'

echo  # newline after stream

# ── Python alternative using httpx ──────────────────────────────────────────
# Uncomment to run:
#
# python3 - <<'EOF'
# import httpx, json
#
# with httpx.Client() as client:
#     with client.stream(
#         "POST",
#         f"http://localhost:19001/v1/sessions/{SESSION_ID}/chat/stream",
#         json={"message": "Explain machine learning."},
#     ) as r:
#         for line in r.iter_lines():
#             if line.startswith("data:"):
#                 data = json.loads(line[5:])
#                 if "text" in data:
#                     print(data["text"], end="", flush=True)
# EOF
