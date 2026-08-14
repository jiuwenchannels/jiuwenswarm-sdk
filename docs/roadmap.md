# Roadmap

This document tracks every remaining implementation task required to reach
the v1.0.0 release. When the last item here is checked off, the roadmap
section becomes empty and v1.0.0 ships.

Features planned *beyond* v1.0.0 are collected at the bottom under
**Future / v2**.

---

> All v1.0.0 implementation tasks are complete. v1.0.0 is ready to ship.
> Run `git tag v1.0.0 && git push --tags` to trigger the publish pipeline.

---

## v2 Roadmap

Phases are ordered by dependency: each phase unblocks the next.
Phases A and B are independent of each other and can run in parallel.
Phases C–F must be sequential. Phase G can start once Phase B is stable.

---

## Phase A — Additional Evaluation Metrics

No infrastructure dependencies. Adds to the existing `openjiuwen/sdk/optimize/eval.py`
module and the `MetricEvaluator` pipeline.

### `RougeMetric`

| Task | File | Done when |
|---|---|---|
| `RougeMetric(variants=["rouge1","rouge2","rougeL"])` using `rouge-score` library | `openjiuwen/sdk/optimize/eval.py` | Returns per-variant F1 scores; `passed` when mean F1 ≥ threshold |
| Add `rouge-score` to `[optimize]` optional extra | `pyproject.toml` | `pip install openjiuwen-sdk[optimize]` installs it |
| Unit tests | `tests/unit/sdk/test_eval_rouge.py` | 5+ cases: exact match, partial overlap, empty string, multi-sentence |

### `SemanticSimilarityMetric`

| Task | File | Done when |
|---|---|---|
| `SemanticSimilarityMetric(model="text-embedding-3-small", threshold=0.85)` | `openjiuwen/sdk/optimize/eval.py` | Computes cosine similarity between `expected` and `prediction` embeddings via the SDK's configured LLM provider; `passed` when similarity ≥ threshold |
| Lazy embedding call — only invoked during `evaluate()`, not at construction | `openjiuwen/sdk/optimize/eval.py` | No API call on `SemanticSimilarityMetric()` |
| Unit tests (mock embedding responses) | `tests/unit/sdk/test_eval_semantic.py` | Tests for high-similarity pass, low-similarity fail, threshold boundary |

### `ToolUsageMetric`

| Task | File | Done when |
|---|---|---|
| `ToolUsageMetric(required=["tool_a"], forbidden=["tool_b"])` | `openjiuwen/sdk/optimize/eval.py` | Inspects `EvalCase.metadata["tool_calls"]` list; fails if required tool absent or forbidden tool present |
| `EvalCase.metadata` schema for tool call recording | `openjiuwen/sdk/optimize/eval.py` | `{"tool_calls": [{"name": str, "args": dict, "result": str}]}` — documented |
| Unit tests | `tests/unit/sdk/test_eval_tool_usage.py` | Required present, required missing, forbidden present, empty call list |

### `CodeExecutionMetric`

| Task | File | Done when |
|---|---|---|
| `CodeExecutionMetric(language="python", timeout_s=5)` | `openjiuwen/sdk/optimize/eval.py` | Extracts fenced code block from `prediction`; executes in subprocess with `sys.executable`; compares stdout to `expected` |
| Sandboxing: subprocess runs with `resource` limits (max RSS, CPU time) on POSIX; `subprocess` timeout on all platforms | `openjiuwen/sdk/optimize/eval.py` | Runaway code is killed; `passed=False` with `error="timeout"` |
| Unit tests | `tests/unit/sdk/test_eval_code.py` | Correct output passes; wrong output fails; infinite loop times out; syntax error fails gracefully |

---

## Phase B — WebSocket Protocol v2

Introduces binary framing (MessagePack) and structured tool schemas.
Fully backwards-compatible: clients negotiate via the `connect` envelope.
Must be complete before Phase G (native SDKs) begins.

### Server-side (Python gateway)

| Task | File | Done when |
|---|---|---|
| Add `msgpack>=1.0` to `[gateway]` optional extra | `pyproject.toml` | Installed with gateway |
| `protocol_version` field in `connect` envelope: `"1"` (JSON) or `"2"` (msgpack) | `openjiuwen/gateway/ws/dispatcher.py` | Server reads the field and stores preferred encoding on `ConnectionState` |
| Binary WS frames: encode all outbound envelopes with msgpack when client requested v2 | `openjiuwen/gateway/ws/router.py` | `websocket.send_bytes(msgpack.packb(env))` for v2 clients; `send_text` for v1 |
| Receive binary frames from v2 clients | `openjiuwen/gateway/ws/router.py` | `websocket.iter_bytes()` for v2 path; existing text path for v1 |
| Structured tool schema in `tool_call` envelope: `parameters` follows JSON Schema draft-07 | `openjiuwen/gateway/ws/dispatcher.py` | `tool_call` includes `{"parameters": {"type":"object","properties":{...},"required":[...]}}` |
| Unit tests | `tests/unit/gateway/test_ws_v2.py` | v1 client gets text frames; v2 client gets binary frames; tool schema present |

### Client-side (TypeScript SDK)

| Task | File | Done when |
|---|---|---|
| Add `@msgpack/msgpack` dependency | `packages/sdk/package.json` | `npm install` succeeds |
| `ClientConfig.protocolVersion: 1 \| 2` (default: `1`) | `packages/sdk/src/protocol/types.ts` | Existing clients unaffected |
| Send `protocol_version: "2"` in `connect` envelope when configured | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Field present in the connect JSON payload |
| Switch to `ws.binaryType = "arraybuffer"` and msgpack decode when v2 | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Binary frames decoded correctly; `parseEnvelope` accepts `ArrayBuffer \| string` |
| `ToolCallEnvelope.parameters` typed as JSON Schema object | `packages/sdk/src/protocol/types.ts` | Field present in type; not present for v1 tool calls |
| Unit tests | `packages/sdk/tests/ws_v2.test.ts` | v2 client decodes msgpack; `parameters` field accessible |

---

## Phase C — OAuth 2.0 / OIDC in Gateway

Prerequisite for all hosted-mode features (D, E, F).
Introduces the concept of an authenticated **user** owning sessions and agents.

### OIDC discovery and token validation

| Task | File | Done when |
|---|---|---|
| `OAuthConfig` dataclass: `issuer_url`, `client_id`, `audience`, `jwks_cache_ttl_s` | `openjiuwen/gateway/config.py` | Integrated into `GatewayConfig` alongside existing `auth_token` |
| `JWKSCache` — fetches and caches JWKS from `{issuer_url}/.well-known/jwks.json` | `openjiuwen/gateway/auth.py` | Refreshes on TTL expiry; thread-safe |
| `OAuthMiddleware` — validates `Authorization: Bearer <jwt>` using JWKS; extracts `sub`, `email`, `scope` | `openjiuwen/gateway/auth.py` | Invalid/expired JWT → 401; missing → 401 (unless `auth=None`); sets `request.state.user` |
| `request.state.user: UserContext` — `{sub: str, email: str \| None, scopes: list[str]}` | `openjiuwen/gateway/auth.py` | Available in all route handlers |
| Unit tests (RS256 JWT fixture, mock JWKS endpoint) | `tests/unit/gateway/test_oauth.py` | Valid token passes; expired fails; wrong audience fails; missing fails |

### Session and agent isolation

| Task | File | Done when |
|---|---|---|
| `SessionStore` and `CheckpointStore` keyed by `(user_sub, id)` — users cannot access each other's sessions | `openjiuwen/gateway/_registry.py` | `GET /v1/sessions` returns only the caller's sessions |
| `AgentRegistry` per-user lazy instantiation | `openjiuwen/gateway/_registry.py` | Each user gets an isolated agent instance; no shared state across users |
| Update all REST routes to pass `user.sub` into store operations | `openjiuwen/gateway/rest/*.py` | 404 returned when accessing another user's resource (not 403, to avoid enumeration) |
| Unit tests | `tests/unit/gateway/test_user_isolation.py` | User A cannot read, modify, or delete User B's sessions, checkpoints, or knowledge bases |

### WS gateway user identity

| Task | File | Done when |
|---|---|---|
| `connect` envelope accepts `token` field (JWT) for browser clients that cannot set headers | `openjiuwen/gateway/ws/dispatcher.py` | Token validated on `connect`; `ConnectionState.user` populated |
| Reject `chat`/`create_session` before a valid `connect` when OAuth is enabled | `openjiuwen/gateway/ws/dispatcher.py` | Server sends `{"type":"error","message":"not authenticated"}` |
| Unit tests | `tests/unit/gateway/test_ws_auth.py` | Unauthenticated chat rejected; authenticated passes; wrong token rejected |

---

## Phase D — Rate Limiting and Per-Token Quotas

Requires Phase C (user identity). Requires a Redis instance for shared counters.

### Infrastructure

| Task | File | Done when |
|---|---|---|
| Add `redis[asyncio]>=5.0` to `[gateway]` optional extra | `pyproject.toml` | Installed with gateway |
| `RateLimitConfig` in `GatewayConfig`: `requests_per_minute`, `tokens_per_day`, `redis_url` | `openjiuwen/gateway/config.py` | Merged into gateway startup |
| `RedisCounterStore` — async increment/get/expire wrappers around `redis.asyncio` | `openjiuwen/gateway/ratelimit.py` | Key pattern: `rl:{user_sub}:rpm` and `rl:{user_sub}:tpd` |

### Request-level limiting

| Task | File | Done when |
|---|---|---|
| `RateLimitMiddleware` — checks + increments `requests_per_minute` counter; returns 429 with `Retry-After` header on exceed | `openjiuwen/gateway/ratelimit.py` | Sliding window (60 s TTL); applies to all `/v1/` routes except `/v1/health` |
| Unit tests (mock Redis) | `tests/unit/gateway/test_ratelimit.py` | Under limit passes; over limit → 429; header present |

### Token-level quotas

| Task | File | Done when |
|---|---|---|
| Token counter hook in streaming routes: count tokens emitted per response | `openjiuwen/gateway/rest/sessions.py`, `agents.py` | Each SSE token and WS `token` envelope increments `rl:{user_sub}:tpd` |
| `GET /v1/usage` — returns `{requests_today, tokens_today, quota_requests, quota_tokens}` | `openjiuwen/gateway/rest/usage.py` | Values read from Redis; resets at UTC midnight |
| 429 when daily token quota exceeded mid-stream: send error envelope, close stream | `openjiuwen/gateway/rest/sessions.py` | Partial response with error at quota boundary |
| Unit tests | `tests/unit/gateway/test_token_quota.py` | Under quota streams fully; over quota mid-stream gets error |

---

## Phase E — Webhooks

Requires Phase C (user identity) for ownership. Requires Phase D Redis for job queuing
(or a standalone queue; ARQ recommended as it builds on the existing Redis dep).

### Webhook registration

| Task | File | Done when |
|---|---|---|
| `WebhookSpec` model: `url`, `events: list[str]`, `secret: str` | `openjiuwen/gateway/webhooks.py` | Validated with pydantic; secret min 16 chars enforced |
| `POST /v1/webhooks` — register a webhook for the authenticated user | `openjiuwen/gateway/rest/webhooks.py` | Stored per-user in Redis (`wh:{user_sub}:{id}`); 201 response |
| `GET /v1/webhooks` — list user's webhooks | `openjiuwen/gateway/rest/webhooks.py` | Returns array; secret field masked (`wh_***`) |
| `DELETE /v1/webhooks/{id}` | `openjiuwen/gateway/rest/webhooks.py` | 204 on success; 404 if not owned by caller |
| Unit tests | `tests/unit/gateway/test_webhooks_crud.py` | CRUD lifecycle; secret masking; wrong-user 404 |

### Event delivery

| Task | File | Done when |
|---|---|---|
| ARQ worker task `deliver_webhook(event, payload, webhook_id)` — POST to `url` with `X-JiuwenSwarm-Signature: sha256=...` HMAC header | `openjiuwen/gateway/workers/webhook_worker.py` | Delivery attempted; 2xx = success; non-2xx = retry |
| Retry schedule: 30 s → 5 min → 30 min → 2 h → give up after 5 attempts | `openjiuwen/gateway/workers/webhook_worker.py` | Each failure re-enqueues with backoff; `dead_letter` key written on final failure |
| Events fired on: `session.done`, `agent.run.done`, `checkpoint.saved`, `eval.batch.done` | Gateway route files | `arq.create_pool` enqueue after each gateway operation |
| `GET /v1/webhooks/{id}/deliveries` — last 50 delivery attempts with status and response code | `openjiuwen/gateway/rest/webhooks.py` | Stored in Redis list; capped at 50 per webhook |
| Unit tests (mock httpx, mock ARQ) | `tests/unit/gateway/test_webhook_delivery.py` | Signature correct; retry on 500; no retry on 200; dead letter after 5 |

---

## Phase F — SDK Dashboard and Usage Analytics

Requires Phase C (auth), Phase D (usage counters), Phase E (webhook events).
Delivers a self-hosted web UI served by the gateway.

### Analytics backend

| Task | File | Done when |
|---|---|---|
| `AnalyticsEvent` — written to Redis Stream (`analytics:{user_sub}`) on each gateway operation | `openjiuwen/gateway/analytics.py` | Fields: `event`, `timestamp`, `session_id`, `agent_id`, `token_count`, `latency_ms` |
| `GET /v1/analytics/summary` — aggregated counts for `[from, to]` range: total requests, total tokens, p50/p95 latency, top agents | `openjiuwen/gateway/rest/analytics.py` | Reads from Redis Stream with `XRANGE`; computed in-process |
| `GET /v1/analytics/timeseries` — per-hour or per-day bucketed token + request counts | `openjiuwen/gateway/rest/analytics.py` | Returns `{timestamps: [], requests: [], tokens: []}` arrays |
| Unit tests (mock Redis Stream) | `tests/unit/gateway/test_analytics.py` | Aggregation correct; date range filtering works |

### Dashboard frontend

| Task | File | Done when |
|---|---|---|
| Single-page dashboard: `GET /dashboard` serves static HTML + JS bundle | `openjiuwen/gateway/dashboard/` | Built with Vite + vanilla TS (no framework dependency); bundled into the Python package |
| Session list view: title, agent, created time, message count | Dashboard | Fetches `GET /v1/sessions` |
| Usage chart: token consumption over time (last 7 days) | Dashboard | Fetches `/v1/analytics/timeseries`; renders with `Chart.js` |
| Webhook management UI: list, create, delete, delivery log | Dashboard | CRUD against `/v1/webhooks` |
| Auth flow: OIDC login button → redirect → JWT stored in `sessionStorage` | Dashboard | Works with any OIDC provider configured in `OAuthConfig` |
| `dashboard` optional extra: `pip install openjiuwen-sdk[gateway,dashboard]` includes built assets | `pyproject.toml` | Assets in `openjiuwen/gateway/dashboard/dist/` included in wheel |

---

## Phase G — Native SDKs (Go, Rust, Java)

Start after Phase B (WS protocol v2) is merged and stable.
All three implement the same WS v2 envelope protocol and REST client.
Each lives in a separate repository / package namespace.

### Go SDK (`github.com/jiuwenswarm/sdk-go`)

| Task | File | Done when |
|---|---|---|
| Module scaffold: `go.mod`, `go.sum` | `sdk-go/` | `go build ./...` succeeds |
| `Envelope` types and msgpack codec | `sdk-go/protocol/` | Encode/decode round-trips match Python reference |
| `Client` struct: `Connect()`, `Disconnect()`, `Send()`, `SendEnvelope()` | `sdk-go/client/client.go` | Connect/disconnect lifecycle; streaming via channel `<-chan string` |
| `SessionManager`: `List()`, `Create()`, `SetActive()`, `Refresh()`, `Active()` | `sdk-go/session/manager.go` | Mirrors Python/TS API |
| Auto-reconnect with exponential back-off | `sdk-go/client/reconnect.go` | Same delay sequence; context-cancellable |
| Unit tests | `sdk-go/*_test.go` | Mock WS server using `nhooyr.io/websocket`; all lifecycle paths covered |
| `go get github.com/jiuwenswarm/sdk-go` works | CI | Published to pkg.go.dev |

### Rust SDK (`crates.io/jiuwenswarm-sdk`)

| Task | File | Done when |
|---|---|---|
| Crate scaffold: `Cargo.toml`, `src/lib.rs` | `sdk-rust/` | `cargo build` succeeds |
| Envelope types with `serde` + `rmp-serde` (msgpack) | `sdk-rust/src/protocol.rs` | Derive `Serialize`/`Deserialize`; round-trip test passes |
| Async `Client` with `tokio-tungstenite` | `sdk-rust/src/client.rs` | `client.connect().await`; `client.send(msg).await` returns `impl Stream<Item=String>` |
| `SessionManager` | `sdk-rust/src/session.rs` | Same API shape as Go/TS |
| Auto-reconnect using `tokio::time::sleep` | `sdk-rust/src/client.rs` | Configurable back-off; cancellable via `CancellationToken` |
| Unit tests + doc tests | `sdk-rust/tests/` | Mock WS server with `tokio::net::TcpListener`; all paths |
| Published to `crates.io` | CI | `cargo add jiuwenswarm-sdk` works |

### Java SDK (`com.jiuwenswarm:sdk`)

| Task | File | Done when |
|---|---|---|
| Gradle project: `build.gradle.kts`, `settings.gradle.kts` | `sdk-java/` | `./gradlew build` succeeds |
| Envelope types with `jackson-dataformat-msgpack` | `sdk-java/src/main/java/.../protocol/` | Codec round-trip test passes |
| `JiuwenSwarmClient` using Java 21 virtual threads + `java.net.http.HttpClient` WebSocket API | `sdk-java/src/main/java/.../client/JiuwenSwarmClient.java` | `connect()` returns `CompletableFuture<Void>`; `send()` returns `CompletableFuture<Void>` with `Consumer<String>` token callback |
| `SessionManager` | `sdk-java/src/main/java/.../session/SessionManager.java` | Same lifecycle as Go/Rust/TS |
| Auto-reconnect using `ScheduledExecutorService` | `sdk-java/src/main/java/.../client/` | Configurable delays; `close()` cancels |
| Unit tests with JUnit 5 + WireMock | `sdk-java/src/test/` | All client lifecycle paths |
| Published to Maven Central | CI | `implementation("com.jiuwenswarm:sdk:2.0.0")` resolves |
