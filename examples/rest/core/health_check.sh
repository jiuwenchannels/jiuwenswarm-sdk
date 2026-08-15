#!/usr/bin/env bash
# 01_health_check.sh — verify the JiuwenSwarm HTTP gateway is running.
#
# Prerequisites:
#   jiuwenswarm serve   (starts the gateway on port 19001 by default)
#
# Expected response:
#   { "status": "ok", "version": "0.1.0", "protocol_version": "1" }

curl http://localhost:19001/v1/health
