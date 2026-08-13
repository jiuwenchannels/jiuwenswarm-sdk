# Roadmap

This document tracks every remaining implementation task required to reach
the v1.0.0 release. When the last item here is checked off, the roadmap
section becomes empty and v1.0.0 ships.

Features planned *beyond* v1.0.0 are collected at the bottom under
**Future / v2**.

---

## Phase 2 completion — System tests

Phase 2 code (Agent, Session, @tool, Team, EventEmitter) is done.
The system tests that verify everything against a live local server remain.

| Task | File | Done when |
|---|---|---|
| Integration test: connect, create session, stream response | `tests/system_tests/sdk/test_agent_stream.py` | Against a real local server; marked `@pytest.mark.system`; skipped in CI |
| Integration test: custom tool invoked by agent | `tests/system_tests/sdk/test_custom_tool.py` | Agent calls the registered tool and returns its result in the final response |
| Integration test: session persistence (create, send, history) | `tests/system_tests/sdk/test_session.py` | Session history returns correct messages after a chat exchange |

---

## Phase 2 completion — Advanced Python SDK modules

All of the following modules are documented in `docs/api-reference.md` and
exercised in `examples/python/` but their `openjiuwen/sdk/` implementation
does not exist yet. Each row is one bridge + façade + unit test file.

### Memory and knowledge

| Task | File | Done when |
|---|---|---|
| `Memory` façade + `memory_bridge.py` | `openjiuwen/sdk/memory.py` | `Memory.create(agent)` → attaches in-process memory; `memory.add(text)`, `memory.search(query)` work |
| Unit tests | `tests/unit_tests/sdk/test_memory.py` | add, search, clear all tested with mocked bridge |
| `KnowledgeBase` façade + `knowledge_bridge.py` | `openjiuwen/sdk/knowledge.py` | `KnowledgeBase.create(name)`, `.add_documents([...])`, `.query(text)` work |
| Unit tests | `tests/unit_tests/sdk/test_knowledge.py` | create, add, query, error propagation |
| `AgenticRetriever` façade | `openjiuwen/sdk/knowledge.py` | `AgenticRetriever(kb)` exposes `retrieve(query, max_hops)` with multi-round rewriting |
| Unit tests | `tests/unit_tests/sdk/test_retriever.py` | single-hop, multi-hop, fallback to direct query |
| `GraphKnowledgeBase` façade | `openjiuwen/sdk/knowledge.py` | `GraphKnowledgeBase.create(name)`, `.add_entity(id, text, links)`, `.query(text)` work |
| Unit tests | `tests/unit_tests/sdk/test_graph_kb.py` | add entities, query, traverse links |

### Multimodal

| Task | File | Done when |
|---|---|---|
| `MultimodalAgent` façade + `Attachment` dataclass | `openjiuwen/sdk/multimodal.py` | `MultimodalAgent.create(name)`, `agent.run(prompt, attachments=[...])` work; `Attachment.from_file(path)` produces a typed object |
| Unit tests | `tests/unit_tests/sdk/test_multimodal.py` | image attachment round-trip; unsupported MIME raises `SdkError` |

### Evaluation

| Task | File | Done when |
|---|---|---|
| `Evaluator`, `ExactMatchMetric`, `LLMAsJudgeMetric` | `openjiuwen/sdk/evaluation.py` | `Evaluator(metrics=[ExactMatchMetric()])`, `.run(cases)` returns `EvalResult` |
| `HITTEvaluator` | `openjiuwen/sdk/evaluation.py` | Wraps `EvalResult` to estimate human-in-the-loop effort |
| Unit tests | `tests/unit_tests/sdk/test_evaluation.py` | exact match pass/fail, LLM judge (mocked), HITT score |

### Observability

| Task | File | Done when |
|---|---|---|
| `OtelTracer` façade + `OtelTracerConfig` | `openjiuwen/sdk/tracing.py` | `OtelTracer(config).instrument(agent)` attaches OpenTelemetry spans to every `agent.run` and `stream` call |
| Unit tests | `tests/unit_tests/sdk/test_tracing.py` | span created on run; attributes contain agent name, session id |

### Workspace

| Task | File | Done when |
|---|---|---|
| `Workspace` façade + `WorkspaceConfig` | `openjiuwen/sdk/workspace.py` | `Workspace(config)`, `.read(path)`, `.write(path, content)`, `.run_command(cmd)` work; sandbox mode blocks paths outside `root` |
| Unit tests | `tests/unit_tests/sdk/test_workspace.py` | read, write, run_command; sandbox path escape raises `SdkError` |

### Checkpointing backends

| Task | File | Done when |
|---|---|---|
| `InMemoryCheckpointBackend` | `openjiuwen/sdk/contrib/memory_checkpoint.py` | Implements `CheckpointerBackend`; save and load a checkpoint by opaque ID |
| `RedisCheckpointBackend` | `openjiuwen/sdk/contrib/redis_checkpoint.py` | Same protocol; connects to Redis via `redis-py`; optional dependency |
| Unit tests | `tests/unit_tests/sdk/test_checkpoint_backends.py` | save + load round-trip for both backends |

### Swarm orchestration

| Task | File | Done when |
|---|---|---|
| `SwarmFlow` façade + `swarm_bridge.py` | `openjiuwen/sdk/swarm.py` | `SwarmFlow.create(agents, strategy)`, `.run(prompt)` returns `SwarmResult`; `best_of` and `majority_vote` strategies wired |
| Unit tests | `tests/unit_tests/sdk/test_swarm.py` | both strategies, empty result, error propagation |

### Multi-rollout

| Task | File | Done when |
|---|---|---|
| `MultiRollout` façade + `MultiRolloutConfig` | `openjiuwen/sdk/rollout.py` | `MultiRollout(agent, config)`, `.run(prompt)` returns `RolloutResult` with `best` and `all` fields |
| Unit tests | `tests/unit_tests/sdk/test_rollout.py` | n=4 rollouts, best_of and majority_vote |

### Permission engine

| Task | File | Done when |
|---|---|---|
| `PermissionEngine` façade + `permission_bridge.py` | `openjiuwen/sdk/permissions.py` | `PermissionEngine(rules)`, `engine.check(agent_id, tool_name)` returns bool; pluggable rule list |
| Unit tests | `tests/unit_tests/sdk/test_permissions.py` | allow/deny by tool name, by agent id, wildcard |

### Context engine

| Task | File | Done when |
|---|---|---|
| `ContextEngine` façade | `openjiuwen/sdk/context.py` | `ContextEngine(agent)`, `.compress()`, `.inject(text)`, `.token_count()` work |
| Unit tests | `tests/unit_tests/sdk/test_context.py` | inject, compress, token count |

### Language server integration

| Task | File | Done when |
|---|---|---|
| `LSPIntegration` façade | `openjiuwen/sdk/lsp.py` | `LSPIntegration.attach(agent, server_cmd)`, `.complete(uri, pos)`, `.diagnose(uri)` work |
| Unit tests | `tests/unit_tests/sdk/test_lsp.py` | complete and diagnose calls routed through mocked bridge |

### Online RL

| Task | File | Done when |
|---|---|---|
| `OnlineRL` façade + `RLConfig` | `openjiuwen/sdk/rl.py` | `OnlineRL(agent, config)`, `.step(prompt, reward_fn)` executes one RL step; `RLConfig.algorithm` wired for `ppo`, `dpo`, `grpo` |
| Unit tests | `tests/unit_tests/sdk/test_rl.py` | step, config validation, reward propagation |

### Agent and prompt builders

| Task | File | Done when |
|---|---|---|
| `AgentBuilder` façade | `openjiuwen/sdk/builder.py` | `AgentBuilder(name)` fluent builder: `.with_model()`, `.with_tools()`, `.with_hooks()`, `.with_memory()` → `.build()` returns `Agent` |
| `PromptBuilder` façade | `openjiuwen/sdk/builder.py` | `PromptBuilder()` fluent builder: `.system()`, `.user()`, `.few_shot()` → `.build()` returns str |
| Unit tests | `tests/unit_tests/sdk/test_builder.py` | full AgentBuilder chain; PromptBuilder outputs correct string |

### Sub-workflows

| Task | File | Done when |
|---|---|---|
| `SubWorkflowNode` dataclass | `openjiuwen/sdk/workflow.py` | `workflow.add_node("sub", SubWorkflowNode(workflow=inner))` runs inner workflow as a node |
| Handle in `workflow_bridge.py` | `openjiuwen/sdk/_internal/workflow_bridge.py` | `_node_to_component` maps `SubWorkflowNode` to the runtime sub-workflow component |
| Unit tests | `tests/unit_tests/sdk/test_workflow.py` | nested workflow execute, input/output mapping |

### MCP server

| Task | File | Done when |
|---|---|---|
| `MCPServer` façade + `mcp_bridge.py` | `openjiuwen/sdk/mcp.py` | `MCPServer(agents)`, `.start(host, port)`, `.stop()` wire a team's agents as MCP endpoints |
| Unit tests | `tests/unit_tests/sdk/test_mcp.py` | start, stop, request routing (mocked bridge) |

---

## Phase 3 — HTTP REST + WebSocket Gateway

### Auth middleware

| Task | File | Done when |
|---|---|---|
| `BearerTokenMiddleware` | `openjiuwen/gateway/auth.py` | Requests without a valid `Authorization: Bearer <token>` return 401; `auth_token=None` disables auth (dev mode) |
| Unit tests | `tests/unit_tests/gateway/test_auth.py` | valid token passes; invalid token → 401; disabled auth passes all |

### REST routes

| Task | File | Done when |
|---|---|---|
| `GET /v1/health` | `openjiuwen/gateway/rest/health.py` | Returns `{status: "ok", version: "...", protocol_version: "1"}` |
| `/v1/sessions` CRUD | `openjiuwen/gateway/rest/sessions.py` | GET list, POST create, GET by id, DELETE — all tested with `httpx.AsyncClient` |
| `POST /v1/sessions/{id}/chat` (blocking) | `openjiuwen/gateway/rest/sessions.py` | Returns full JSON response when agent completes |
| `POST /v1/sessions/{id}/chat/stream` (SSE) | `openjiuwen/gateway/rest/sessions.py` | Returns `text/event-stream`; emits `event: token` per token; closes with `event: done` |
| `GET /v1/agents`, `GET /v1/agents/{id}` | `openjiuwen/gateway/rest/agents.py` | List registered agents and fetch by id |
| `POST /v1/agents/{id}/run` | `openjiuwen/gateway/rest/agents.py` | Blocking agent run |
| `POST /v1/agents/{id}/stream` | `openjiuwen/gateway/rest/agents.py` | SSE agent stream |
| `GET /v1/tools` | `openjiuwen/gateway/rest/tools.py` | Returns all registered tools with name, description, schema |
| `POST /v1/knowledge`, `POST /v1/knowledge/{name}/documents`, `POST /v1/knowledge/{name}/query` | `openjiuwen/gateway/rest/knowledge.py` | Knowledge base CRUD and query |
| `POST /v1/eval/batch` | `openjiuwen/gateway/rest/eval.py` | Batch evaluation endpoint |
| `POST /v1/agents/{id}/checkpoint`, `GET /v1/checkpoints`, `POST /v1/checkpoints/{id}/restore` | `openjiuwen/gateway/rest/checkpoints.py` | Checkpoint save, list, restore |
| Unit tests for all routes | `tests/unit_tests/gateway/` | Each route: success case + at least one 4xx error case |

### WebSocket gateway

| Task | File | Done when |
|---|---|---|
| `/v1/ws` envelope handler | `openjiuwen/gateway/ws/router.py` | Accepts WS connection; parses JSON envelopes; dispatches to runtime |
| `"protocol_version": "1"` in `ack` | `openjiuwen/gateway/ws/dispatcher.py` | Every `ack` payload includes this field |
| `client_type` forwarding | `openjiuwen/gateway/ws/dispatcher.py` | `connect` envelope `client_type` stored and forwarded to agent context |
| `envelope.py` — parse and validate | `openjiuwen/gateway/ws/envelope.py` | `parseEnvelope(raw)` returns typed envelope dict or raises `ProtocolError` |

### FastAPI app assembly

| Task | File | Done when |
|---|---|---|
| `build_gateway_app(config)` | `openjiuwen/gateway/app.py` | Returns a FastAPI app with all routes + auth middleware mounted; accepts `GatewayConfig` |
| `python -m openjiuwen.gateway` entrypoint | `openjiuwen/gateway/__main__.py` | `python -m openjiuwen.gateway --host 0.0.0.0 --port-rest 19001 --port-ws 19000` starts both servers |
| OpenAPI at `/docs` | — | `curl http://localhost:19001/docs` returns Swagger UI HTML |

---

## Phase 4 — TypeScript SDK (`@jiuwenswarm/sdk`)

### Project setup

| Task | File | Done when |
|---|---|---|
| `package.json` with `name`, `main`, `module`, `types`, `exports`, `peerDependencies` | `packages/sdk/package.json` | `npm install` in `packages/sdk/` succeeds |
| `tsconfig.json` | `packages/sdk/tsconfig.json` | `npx tsc --noEmit` passes on the source tree |
| `tsup` for dual CJS + ESM output | `packages/sdk/tsup.config.ts` | `npm run build` produces `dist/index.cjs`, `dist/index.mjs`, `dist/index.d.ts` |
| `vitest` configuration | `packages/sdk/vitest.config.ts` | `npm test` runs and exits cleanly |

### Protocol types and validation

| Task | File | Done when |
|---|---|---|
| `InboundEnvelope`, `OutboundEnvelope`, `SessionInfo`, `AgentMode`, `ChatMessage` | `packages/sdk/src/protocol/types.ts` | Mirrors server protocol exactly; all fields typed |
| `MSG` constants object | `packages/sdk/src/protocol/constants.ts` | All envelope type strings as named constants |
| `parseEnvelope(raw)` | `packages/sdk/src/protocol/validate.ts` | Returns typed envelope or throws `ProtocolError` |
| Unit tests | `packages/sdk/tests/protocol.test.ts` | Valid and invalid payloads all covered |

### EventEmitter

| Task | File | Done when |
|---|---|---|
| Typed `EventEmitter` — no Node.js dependency | `packages/sdk/src/events/EventEmitter.ts` | `on`, `off`, `emit` work in browser and Node.js |
| Unit tests | `packages/sdk/tests/emitter.test.ts` | Register, fire, remove, multiple listeners |

### Reconnect scheduler

| Task | File | Done when |
|---|---|---|
| `ReconnectScheduler` — delay sequence 1→2→5→10→30 s | `packages/sdk/src/client/reconnect.ts` | Tracks attempts; computes delays; calls back at the right time; `cancel()` stops it |
| Unit tests | `packages/sdk/tests/reconnect.test.ts` | Delay sequence verified; cancel stops further callbacks |

### `JiuwenSwarmClient`

| Task | File | Done when |
|---|---|---|
| `connect()` / `disconnect()` | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Opens WebSocket; sends `connect` on open; parses incoming envelopes; dispatches events |
| `send(message)` | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Sends `chat` envelope; `token` events fire during streaming; `done` fires at end |
| `sendEnvelope(type, payload)` | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Low-level send; serialises to JSON |
| `tool_call` auto-rejection | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Any `tool_call` envelope without `onToolCall` returns `{error: "not supported"}` immediately |
| WebSocket detection: browser → Node.js `ws` → `ConnectionError` | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Correct adapter chosen at runtime; `ws` is optional peer dep |
| Unit tests (mock WebSocket) | `packages/sdk/tests/client.test.ts` | connect, send, token/done events, tool_call rejection, reconnect on close |

### `SessionManager`

| Task | File | Done when |
|---|---|---|
| `list()`, `create()`, `setActive()`, `refresh()`, `active` getter | `packages/sdk/src/session/SessionManager.ts` | Sessions populated from `sessions` envelope; active session persists across refresh |
| Unit tests | `packages/sdk/tests/session.test.ts` | All methods; active session persists across refresh |

### Barrel export and docs

| Task | File | Done when |
|---|---|---|
| Re-export all public symbols | `packages/sdk/src/index.ts` | `import { JiuwenSwarmClient, SessionManager } from "@jiuwenswarm/sdk"` resolves in CJS and ESM |
| TypeDoc configuration | `packages/sdk/typedoc.json` | `npm run docs` generates HTML in `packages/sdk/docs/` without errors |

### npm publish

| Task | File | Done when |
|---|---|---|
| `publishConfig` in `package.json` | `packages/sdk/package.json` | `npm publish --dry-run` shows correct contents: `dist/`, `README.md`, no `src/` |
| Publish `1.0.0` to registry | — | `npm install @jiuwenswarm/sdk` works from a fresh project |

---

## Future / v2

These features are intentionally deferred past v1.0.0:

| Feature | Reason |
|---|---|
| Migrate browser extension to `@jiuwenswarm/sdk` | Extension works; migration is additive polish |
| Migrate mobile app to `@jiuwenswarm/sdk` | Same — protocol duplication is acceptable for v1 |
| Go / Rust / Java native SDKs | REST API covers these languages adequately |
| Rate limiting and per-token quotas | Requires hosted multi-tenant mode |
| SDK dashboard and usage analytics | Requires hosted mode |
| Webhooks (async result delivery) | SSE covers synchronous use cases; hosted mode needed for fire-and-forget |
| OAuth 2.0 / OIDC in gateway | Requires multi-tenant auth design |
| WebSocket protocol v2 (binary framing, structured tool schemas) | Protocol is frozen at v1 for the lifetime of v1.0.0 |
| `RougeMetric`, `CodeExecutionMetric`, `SemanticSimilarityMetric`, `ToolUsageMetric` | Nice-to-have after ship |
