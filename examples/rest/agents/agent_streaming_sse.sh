#!/usr/bin/env bash
# 08_agent_streaming_sse.sh — stream a named agent's response via SSE without
# needing a pre-created session.
#
# Prerequisites:
#   jiuwenswarm serve   (starts the gateway on port 19001 by default)

# cURL streaming
curl -N -X POST http://localhost:19001/v1/agents/support-bot/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "A customer says their order has not arrived after 14 days. Draft a reply."}'

echo  # newline after stream

# ── Go alternative ───────────────────────────────────────────────────────────
# Save as main.go and run with:  JIUWENSWARM_TOKEN=... go run main.go
#
# package main
#
# import (
#     "bufio"
#     "fmt"
#     "net/http"
#     "os"
#     "strings"
# )
#
# func main() {
#     token := os.Getenv("JIUWENSWARM_TOKEN")
#     body := strings.NewReader(`{"prompt":"Summarise the HTTP/2 spec in 3 bullet points."}`)
#     req, _ := http.NewRequest("POST", "http://localhost:19001/v1/agents/deep-agent/stream", body)
#     req.Header.Set("Content-Type", "application/json")
#     req.Header.Set("Authorization", "Bearer "+token)
#
#     resp, _ := http.DefaultClient.Do(req)
#     defer resp.Body.Close()
#
#     scanner := bufio.NewScanner(resp.Body)
#     for scanner.Scan() {
#         line := scanner.Text()
#         if strings.HasPrefix(line, "data:") {
#             fmt.Print(strings.TrimPrefix(line, "data: "))
#         }
#     }
# }
