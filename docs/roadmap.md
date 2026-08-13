# Roadmap

This document covers features planned beyond the v1.0.0 release.
For everything currently available, see `docs/overview.md`.

---

## Browser extension and mobile app migration

The browser extension and mobile app both use the WebSocket envelope
protocol directly. They predate the TypeScript SDK and were intentionally
left unchanged for v1. Migrating them to `@jiuwenswarm/sdk` would:

- Eliminate duplicated envelope-parsing code in both clients
- Allow them to benefit from the SDK's reconnect logic, `SessionManager`,
  and typed events
- Simplify adding new protocol features (single change point vs. three)

The migration is non-breaking because the SDK speaks the same envelope
format the server already supports.

---

## Native SDKs for Go, Rust, Java

The REST gateway covers these languages at the HTTP level for v1. For v2,
first-class native SDKs provide streaming support, session management,
and typed interfaces without requiring application developers to write
their own SSE parsers.

Priority order (by likely user demand): **Go** → **Rust** → **Java**.

Each SDK follows the same pattern as the Python and TypeScript SDKs:
- Session and agent concepts mirror the REST API
- Streaming via SSE (not WebSocket, for simplicity)
- No dependency on the JiuwenSwarm runtime — HTTP only

---

## Hosted mode features

These features are only meaningful when JiuwenSwarm is deployed as a
multi-tenant hosted service (not self-hosted). They are out of scope
until a hosted offering is defined:

**Rate limiting and per-token quotas**
- Per-user or per-team token budgets
- Quota enforcement in the gateway middleware
- Usage reporting endpoints (`GET /v1/usage`)

**SDK usage dashboard and analytics**
- Per-agent call volume, latency, error rate
- Token consumption over time
- Exportable to CSV or a metrics backend

**Webhooks (async result delivery)**
- `POST /v1/webhooks` — register a callback URL
- Gateway POSTs `{event, payload}` to the URL when an agent run completes
- Useful for long-running agents triggered by CI/CD or external events
- SSE covers synchronous use cases; webhooks cover fire-and-forget

---

## Advanced auth and multi-tenancy

- OAuth 2.0 / OIDC integration in the gateway
- Per-tenant token scoping (tenant A cannot see tenant B sessions)
- Audit logging of all agent runs and tool calls

---

## Protocol version 2

The WebSocket envelope protocol is frozen at version `"1"` for the
lifetime of v1. Breaking changes (removing or renaming fields) require a
`protocol_version: "2"` in `ack` payloads and a `/v2/ws` endpoint.

Candidates for v2:
- Structured tool-call envelopes with typed argument schemas
- Binary framing (MessagePack) for high-throughput streaming
- Server-sent heartbeat / ping-pong frames

---

## Additional evaluation metrics

The v1 evaluation framework ships `ExactMatchMetric` and
`LLMAsJudgeMetric`. Planned additions:

- `RougeMetric` — ROUGE-L for summarisation tasks
- `CodeExecutionMetric` — run generated code and check exit code / output
- `SemanticSimilarityMetric` — cosine similarity via embeddings
- `ToolUsageMetric` — whether the agent used the expected tools
