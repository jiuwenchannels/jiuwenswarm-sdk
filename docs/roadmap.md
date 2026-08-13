# Roadmap

What is currently built is described in `docs/overview.md`.
This document covers everything not yet built.

---

## Phase 2 — System tests

These tests exercise the full stack against a live local server.
They are marked `@pytest.mark.system` and skipped in CI by default.

| Task | File | Done when |
|------|------|-----------|
| Agent streaming system test | `tests/system_tests/sdk/test_agent_stream.py` | `await agent.stream("hello")` yields tokens from a real model against a local server |
| Custom tool invocation system test | `tests/system_tests/sdk/test_custom_tool.py` | Agent calls a registered `@tool` and the result appears in the final response |
| Session persistence system test | `tests/system_tests/sdk/test_session.py` | Session `history()` returns the correct messages after a real chat exchange |

**Done when:** All three tests pass manually against a local server. The `examples/python/08_multi_agent_team.py` team example also runs successfully end-to-end.

---

## Phase 2 — Python SDK: advanced features

These correspond to §6–§29 in the usage examples. The example files
already exist in `examples/python/`; the SDK implementation does not yet.

### §6 — Long-term memory

| Task | File | Done when |
|------|------|-----------|
| `MemoryScope` enum (`USER`, `SESSION`, `GLOBAL`) | `openjiuwen/sdk/memory.py` | `from openjiuwen.sdk import MemoryScope` works |
| `Memory` class with `add`, `search`, `delete`, `list` | `openjiuwen/sdk/memory.py` | `await agent.memory.search("query")` returns ranked results |
| Bridge: `sdk/_internal/memory_bridge.py` | `memory_bridge.py` | Wraps core memory manager; patchable module-level functions |
| `Agent.create(memory_scope=MemoryScope.USER)` | `sdk/agent.py` | Scope is forwarded to the bridge and stored in agent context |
| Unit tests | `tests/unit_tests/sdk/test_memory.py` | add, search, delete, list; scope forwarding |

### §7 — Knowledge base and RAG

| Task | File | Done when |
|------|------|-----------|
| `KnowledgeBase.create(name, embedding_model, vector_store)` | `openjiuwen/sdk/knowledge.py` | Creates and registers a named vector store |
| `kb.add_documents(docs)` | `openjiuwen/sdk/knowledge.py` | Chunks, embeds, and indexes documents; returns doc IDs |
| `Retriever(kb, strategy)` with `"hybrid"`, `"vector"`, `"bm25"` | `openjiuwen/sdk/knowledge.py` | `await retriever.retrieve("query", top_k=5)` returns ranked results |
| `Agent.create(knowledge_bases=[kb])` | `sdk/agent.py` | KB context injected automatically on each agent run |
| Bridge: `sdk/_internal/knowledge_bridge.py` | `knowledge_bridge.py` | Wraps core knowledge manager |
| Unit tests | `tests/unit_tests/sdk/test_knowledge.py` | create, add, retrieve, agent integration |

### §9 — SwarmFlow structured orchestration

| Task | File | Done when |
|------|------|-----------|
| `parallel(agents, prompt)` | `openjiuwen/sdk/swarmflow.py` | Fan-out to all agents simultaneously; returns `list[AgentResult]` |
| `pipeline(agents, prompt)` | `openjiuwen/sdk/swarmflow.py` | Chains agents so each output feeds the next |
| `phase(groups)` | `openjiuwen/sdk/swarmflow.py` | Executes groups sequentially; agents within a group run in parallel |
| `run_swarmflow(spec, prompt)` | `openjiuwen/sdk/swarmflow.py` | Top-level entry point accepting a nested `parallel`/`pipeline`/`phase` spec |
| Unit tests | `tests/unit_tests/sdk/test_swarmflow.py` | parallel, pipeline, phase, nested compositions |

### §10 — Evaluation framework

| Task | File | Done when |
|------|------|-----------|
| `EvalCase(input, expected, metadata)` dataclass | `openjiuwen/sdk/eval.py` | Importable from `openjiuwen.sdk` |
| `Metric` protocol with `score(prediction, expected) -> float` | `openjiuwen/sdk/eval.py` | Custom classes implement `Metric` |
| `ExactMatchMetric`, `LLMAsJudgeMetric` | `openjiuwen/sdk/eval.py` | Both return 0.0–1.0 |
| `MetricEvaluator(agent, metrics)` | `openjiuwen/sdk/eval.py` | `await evaluator.run(cases)` returns `EvalResult` with per-case scores and summary |
| Unit tests | `tests/unit_tests/sdk/test_eval.py` | ExactMatch, LLMAsJudge, custom metric, batch evaluation |

### §11 — OpenTelemetry observability

| Task | File | Done when |
|------|------|-----------|
| `OtelTracerConfig(service_name, endpoint, insecure)` | `openjiuwen/sdk/observability.py` | Frozen dataclass; importable from `openjiuwen.sdk` |
| `init_otel_tracer(config)` | `openjiuwen/sdk/observability.py` | Configures a gRPC OTLP exporter; subsequent agent/tool/LLM calls emit spans |
| Span creation for agent run, tool call, LLM call | internal instrumentation | Each operation visible as a named span in any OTLP collector |
| Unit tests | `tests/unit_tests/sdk/test_observability.py` | Tracer initialised; spans created on mocked runs |

### §12 — Workspace

| Task | File | Done when |
|------|------|-----------|
| `Workspace(root, sandbox)` | `openjiuwen/sdk/workspace.py` | Binds to a directory; `sandbox=True` isolates file/shell ops |
| `workspace.diff()` | `openjiuwen/sdk/workspace.py` | Returns git diff of working tree relative to workspace root |
| `workspace.modified_files` property | `openjiuwen/sdk/workspace.py` | Returns list of modified file paths |
| `Agent.create(workspace=ws)` | `sdk/agent.py` | Agent tools receive workspace context; sandbox enforced |
| Unit tests | `tests/unit_tests/sdk/test_workspace.py` | diff, modified_files, sandbox enforcement |

### §13 — Checkpoint/restore — full backend integration

| Task | File | Done when |
|------|------|-----------|
| `SessionStore` protocol | `openjiuwen/sdk/stores.py` | `save`, `load`, `delete`, `list` |
| `CheckpointerBackend` protocol | `openjiuwen/sdk/stores.py` | `save_checkpoint`, `load_checkpoint`, `list_checkpoints` |
| `register_store(name, class)`, `register_checkpointer(name, class)` | `openjiuwen/sdk/stores.py` | Registered by string; used in `Agent.create` |
| `Agent.create(checkpoint_store="sqlite", checkpoint_every=5)` | `sdk/agent.py` | Auto-checkpoints every N turns; store constructed from registry |
| Built-in adapters: `SqliteSessionStore`, `SqliteCheckpointer` | `openjiuwen/sdk/stores.py` | Work out-of-the-box with no extra dependencies |
| Unit tests | `tests/unit_tests/sdk/test_stores.py` | register, create, save, load, periodic checkpoint |

### §14 — Multimodal inputs

| Task | File | Done when |
|------|------|-----------|
| `ImageInput.from_file(path)`, `ImageInput.from_url(url)` | `openjiuwen/sdk/multimodal.py` | Returns an `ImageInput` dataclass with base64-encoded content |
| `AudioInput.from_file(path)` | `openjiuwen/sdk/multimodal.py` | Returns an `AudioInput` dataclass |
| `VisionModelConfig`, `AudioModelConfig` subclasses of `ModelConfig` | `openjiuwen/sdk/config.py` | Additional fields for vision/audio model variants |
| `agent.run(prompt, images=[img], audio=[aud])` | `sdk/agent.py` | Inputs forwarded to runtime; model receives multimodal message |
| Unit tests | `tests/unit_tests/sdk/test_multimodal.py` | from_file, from_url, encoding, agent forwarding |

### §15 — Multi-rollout

| Task | File | Done when |
|------|------|-----------|
| `MultiRolloutConfig(n, strategy)` | `openjiuwen/sdk/rollout.py` | `n` parallel runs; `strategy` in `"best_of"`, `"majority_vote"` |
| `MultiRolloutExecutor(agent, config)` | `openjiuwen/sdk/rollout.py` | `await executor.run(prompt)` runs N times concurrently |
| `executor.best_of(prompt, evaluator)` | `openjiuwen/sdk/rollout.py` | Runs N rollouts, scores each with the evaluator, returns the highest |
| Unit tests | `tests/unit_tests/sdk/test_rollout.py` | run N times, best_of selection, error handling |

### §16 — Task loop event hooks (full)

| Task | File | Done when |
|------|------|-----------|
| `TaskLoopEventHandler` base class with all lifecycle methods | `openjiuwen/sdk/task_loop.py` | `on_turn_start`, `on_tool_call`, `on_tool_result`, `on_llm_call`, `on_done`, `on_error` |
| Tool-call interception with early return | `openjiuwen/sdk/task_loop.py` | Handler can return a `ToolResult` from `on_tool_call` to block execution |
| `ToolGuard(allowed_tools)` | `openjiuwen/sdk/task_loop.py` | Raises `ToolError` when the agent calls a tool not in the allow-list |
| `Agent.create(event_handler=handler)` | `sdk/agent.py` | Handler wired into task loop |
| Unit tests | `tests/unit_tests/sdk/test_task_loop.py` | all lifecycle methods, interception, ToolGuard |

### §18 — Sub-workflow composition

| Task | File | Done when |
|------|------|-----------|
| `SubWorkflowComponent(workflow, input_mapping, output_mapping)` | `openjiuwen/sdk/workflow.py` | Embeds one `Workflow` as a node inside another |
| `input_mapping` / `output_mapping` dicts | `openjiuwen/sdk/workflow.py` | Parent state keys mapped to child inputs; child outputs mapped back |
| Bridge support in `workflow_bridge.py` | `_internal/workflow_bridge.py` | `_node_to_component` handles `SubWorkflowComponent` |
| Unit tests | `tests/unit_tests/sdk/test_workflow.py` | sub-workflow creation, mapping, run |

### §19 — Agent builder

| Task | File | Done when |
|------|------|-----------|
| `LlmAgentBuilder` fluent API | `openjiuwen/sdk/builder.py` | `.with_model()`, `.with_tools()`, `.with_memory()`, `.build()` → `Agent` |
| `WorkflowBuilder` fluent API | `openjiuwen/sdk/builder.py` | `.add_step()`, `.branch()`, `.build()` → `Workflow` |
| Unit tests | `tests/unit_tests/sdk/test_builder.py` | builder produces correct Agent/Workflow; missing required fields raise `ConfigError` |

### §20 — Prompt builder

| Task | File | Done when |
|------|------|-----------|
| `MetaTemplateBuilder(agent, n)` | `openjiuwen/sdk/prompt_builder.py` | Generates `n` candidate system prompts from a task description |
| `FeedbackPromptBuilder(agent)` | `openjiuwen/sdk/prompt_builder.py` | `.refine(prompt, bad_cases)` → improved prompt string |
| Unit tests | `tests/unit_tests/sdk/test_prompt_builder.py` | generate, refine, bad-case handling |

### §21 — Custom store and checkpointer backends (third-party)

| Task | File | Done when |
|------|------|-----------|
| `PostgresSessionStore` example adapter | `openjiuwen/sdk/contrib/postgres.py` | Implements `SessionStore`; connects via `asyncpg` |
| `S3Checkpointer` example adapter | `openjiuwen/sdk/contrib/s3.py` | Implements `CheckpointerBackend`; uses `aiobotocore` |
| Registration verified in tests | `tests/unit_tests/sdk/test_stores.py` | `register_store("postgres", PostgresSessionStore)` and use by name |

### §22 — Security rails and permission engine

| Task | File | Done when |
|------|------|-----------|
| `PermissionsSection(tool, level, allow, deny)` | `openjiuwen/sdk/security.py` | Frozen dataclass; `level` in `"allow"`, `"deny"`, `"ask"` |
| `PermissionEngine(sections)` | `openjiuwen/sdk/security.py` | `engine.check(tool_name, args)` returns `PermissionDecision` |
| `CLIApprovalHost` | `openjiuwen/sdk/security.py` | Prompts `y/n` on stdout; used with `level="ask"` |
| `Agent.create(permission_engine=pe)` | `sdk/agent.py` | Engine consulted before each tool call |
| Unit tests | `tests/unit_tests/sdk/test_security.py` | allow, deny, ask with mock host, agent integration |

### §23 — LSP integration

| Task | File | Done when |
|------|------|-----------|
| `lsp.initialize_lsp(server_cmd)` | `openjiuwen/sdk/lsp.py` | Starts LSP process; opens JSON-RPC stdio connection |
| `get_lsp_tool()` | `openjiuwen/sdk/lsp.py` | Returns a `SdkTool` that wraps LSP diagnostics as an agent tool |
| `get_pending_lsp_diagnostics()` | `openjiuwen/sdk/lsp.py` | Returns current diagnostics as a structured list |
| `shutdown_lsp()` | `openjiuwen/sdk/lsp.py` | Sends `shutdown` + `exit` and closes the process |
| Unit tests | `tests/unit_tests/sdk/test_lsp.py` | initialize, diagnostics, shutdown; LSP process mocked |

### §24 — Human-in-the-loop (HITT)

| Task | File | Done when |
|------|------|-----------|
| `TeamRole.HUMAN_AGENT` enum member | `openjiuwen/sdk/team.py` | Role value usable in `TeamMemberSpec` |
| `TeamMemberSpec(role, name, callback)` | `openjiuwen/sdk/team.py` | Spec for a human team member; `callback` called when team sends a message |
| `Team.create(specs, enable_hitt=True)` | `openjiuwen/sdk/team.py` | Team pauses at decision points and awaits human approval callback |
| Unit tests | `tests/unit_tests/sdk/test_team.py` | HUMAN_AGENT spec, enable_hitt, callback invocation |

### §25 — Agentic retrieval

| Task | File | Done when |
|------|------|-----------|
| `AgenticRetriever(base_retriever, llm, max_rounds, top_k_per_round)` | `openjiuwen/sdk/knowledge.py` | Iterates: retrieve → assess → rewrite query → retrieve again |
| `await retriever.retrieve(query)` | `openjiuwen/sdk/knowledge.py` | Stops when confidence threshold met or `max_rounds` reached |
| Unit tests | `tests/unit_tests/sdk/test_knowledge.py` | single-round, multi-round, early stop on confidence |

### §26 — Graph knowledge base

| Task | File | Done when |
|------|------|-----------|
| `GraphKnowledgeBase(name)` | `openjiuwen/sdk/knowledge.py` | Stores documents as subject–predicate–object triples |
| Triple extraction via LLM | internal | Documents parsed into triples on `add_documents()` |
| `GraphKnowledgeBase.query(query, use_graph=True)` | `openjiuwen/sdk/knowledge.py` | Combines vector search with graph traversal |
| Unit tests | `tests/unit_tests/sdk/test_knowledge.py` | add, triple extraction (mocked LLM), combined query |

### §27 — Context engine and compression

| Task | File | Done when |
|------|------|-----------|
| `ContextEngine` with pluggable processors | `openjiuwen/sdk/context_engine.py` | `Agent.create(context_engine=ce)` wires engine into message pipeline |
| `ToolResultBudgetProcessor(max_chars)` | `openjiuwen/sdk/context_engine.py` | Truncates tool results exceeding the budget |
| `MessageSummaryOffloader(threshold)` | `openjiuwen/sdk/context_engine.py` | Summarises old messages when context exceeds threshold |
| `FullCompactProcessor` / `MicroCompactProcessor` | `openjiuwen/sdk/context_engine.py` | Full or incremental context compression |
| `engine.last_stats` property | `openjiuwen/sdk/context_engine.py` | Returns token counts before/after compression |
| Unit tests | `tests/unit_tests/sdk/test_context_engine.py` | each processor, pipeline composition, stats |

### §28 — Online RL and trajectory collection

| Task | File | Done when |
|------|------|-----------|
| `RLConfig(algorithm, lr, batch_size, reward_threshold)` | `openjiuwen/sdk/rl.py` | Frozen dataclass |
| `RewardRegistry` | `openjiuwen/sdk/rl.py` | `register(name, fn)` / `get(name)` |
| `OnlineRLOptimizer(config, reward_registry)` | `openjiuwen/sdk/rl.py` | Wraps agent runs; records `RolloutWithReward`; applies reward-based updates |
| `Agent.create(rl_optimizer=optimizer)` | `sdk/agent.py` | Optimizer hooks into each `run()` call |
| `optimizer.get_trajectories()` | `openjiuwen/sdk/rl.py` | Returns list of recorded `RolloutWithReward` |
| `OfflineRLOptimizer.export_trajectories(path)` | `openjiuwen/sdk/rl.py` | Writes JSONL file for offline training |
| Unit tests | `tests/unit_tests/sdk/test_rl.py` | reward registry, online recording, offline export |

### §29 — MCP server exposure

| Task | File | Done when |
|------|------|-----------|
| `build_server()` function | `openjiuwen/agent_teams/mcp.py` | Returns an `mcp.server.lowlevel.Server` instance wired to the team from `OPENJIUWEN_TEAM_JOIN` |
| `jiuwenswarm_run` tool registration | `openjiuwen/agent_teams/mcp.py` | MCP tool `jiuwenswarm_run(prompt, session_id)` calls the active team and returns the result |
| `python -m openjiuwen.agent_teams.mcp` subprocess mode | `openjiuwen/agent_teams/mcp.py` | Module entrypoint starts stdio server; parent process communicates via JSON-RPC |
| Unit tests | `tests/unit_tests/test_mcp.py` | `build_server()` produces correct tool listing; `jiuwenswarm_run` dispatches correctly (mocked team) |

---

## Phase 3 — HTTP REST + WebSocket Gateway

A standalone FastAPI server that exposes the JiuwenSwarm runtime over
HTTP and WebSocket. Enables cURL, browser fetch, and any language without
a native SDK.

**Dependency:** Phase 2 system tests must pass before Phase 3 begins.

### Step 1 — Auth middleware

| Task | File | Done when |
|------|------|-----------|
| Bearer token middleware | `openjiuwen/gateway/auth.py` | Requests without a valid token return 401 when auth enabled; middleware is a no-op when `auth_token=None` |
| Unit tests | `tests/unit_tests/gateway/test_auth.py` | Valid token passes; invalid token returns 401; disabled auth passes all |

### Step 2 — REST routes

| Task | File | Done when |
|------|------|-----------|
| `GET /v1/health` | `openjiuwen/gateway/rest/health.py` | Returns `{"status":"ok","version":"...","protocol_version":"1"}` |
| `GET/POST/DELETE /v1/sessions` and `GET /v1/sessions/{id}` | `openjiuwen/gateway/rest/sessions.py` | All four endpoints; tested with `httpx.AsyncClient` |
| `POST /v1/sessions/{id}/chat` (blocking) | `openjiuwen/gateway/rest/sessions.py` | Full response as JSON; agent completes before HTTP response |
| `POST /v1/sessions/{id}/chat/stream` (SSE) | `openjiuwen/gateway/rest/sessions.py` | `text/event-stream`; `event: token` lines then `event: done` |
| `GET /v1/agents`, `POST /v1/agents/{id}/run`, `POST /v1/agents/{id}/stream` | `openjiuwen/gateway/rest/agents.py` | List, run blocking, run streaming |
| `GET /v1/tools` | `openjiuwen/gateway/rest/tools.py` | Returns all registered tools |
| `POST /v1/knowledge/{name}/documents`, `POST /v1/knowledge/{name}/query` | `openjiuwen/gateway/rest/knowledge.py` | Document ingestion and query |
| `POST /v1/eval/batch` | `openjiuwen/gateway/rest/eval.py` | Batch eval; returns per-case scores and summary |
| `POST /v1/agents/{id}/checkpoint`, `GET /v1/checkpoints`, `POST /v1/checkpoints/{id}/restore` | `openjiuwen/gateway/rest/checkpoints.py` | Full checkpoint lifecycle |
| Unit tests for all routes | `tests/unit_tests/gateway/` | Each route tested with mocked runtime bridge |

### Step 3 — WebSocket gateway

| Task | File | Done when |
|------|------|-----------|
| `/v1/ws` handler — envelope parsing and dispatch | `openjiuwen/gateway/ws/router.py` | Accepts WS connection; parses JSON envelopes; dispatches to runtime |
| `protocol_version: "1"` in `ack` payloads | `openjiuwen/gateway/ws/dispatcher.py` | `ack` includes `{"protocol_version":"1"}` |
| `client_type` forwarding | `openjiuwen/gateway/ws/dispatcher.py` | `connect` envelope `client_type` stored and passed to agent context |
| Existing clients connect to `/v1/ws` | manual test | Browser extension and mobile app connect; `ack` received; chat works |

### Step 4 — FastAPI app assembly and entrypoint

| Task | File | Done when |
|------|------|-----------|
| `build_gateway_app(config)` function | `openjiuwen/gateway/app.py` | Returns a FastAPI app with all routes mounted; accepts `GatewayConfig` |
| `python -m openjiuwen.gateway` entrypoint | `openjiuwen/gateway/__main__.py` | `python -m openjiuwen.gateway --host 0.0.0.0 --port 19001` starts the server |
| OpenAPI spec at `/docs` | — (FastAPI default) | `curl http://localhost:19001/docs` returns Swagger UI HTML |

**Phase 3 done when:** `python -m openjiuwen.gateway` starts; all REST routes pass unit tests; existing WS clients connect successfully; REST cURL examples in `examples/rest/` run against a live gateway.

---

## Phase 4 — TypeScript / JavaScript SDK

Published as `@jiuwenswarm/sdk` on npm. Connects to the Phase 3 gateway.

**Dependency:** Phase 3 WebSocket gateway must be stable.

### Step 1 — Project setup

| Task | File | Done when |
|------|------|-----------|
| `packages/sdk/` with `package.json`, `tsconfig.json` | `packages/sdk/` | `npm install` succeeds |
| `tsup` for dual CJS + ESM output | `packages/sdk/tsup.config.ts` | `npm run build` produces `dist/index.cjs`, `dist/index.mjs`, `dist/index.d.ts` |
| `vitest` configuration | `packages/sdk/vitest.config.ts` | `npm test` runs and exits cleanly |

### Step 2 — Protocol types

| Task | File | Done when |
|------|------|-----------|
| `InboundEnvelope`, `OutboundEnvelope`, `SessionInfo`, `AgentMode`, `ChatMessage` | `packages/sdk/src/protocol/types.ts` | Mirrors server protocol exactly |
| `MSG` constants object | `packages/sdk/src/protocol/constants.ts` | All envelope type strings |
| `parseEnvelope(raw)` | `packages/sdk/src/protocol/validate.ts` | Returns typed envelope or throws `ProtocolError` |
| Unit tests | `packages/sdk/tests/protocol.test.ts` | Valid and invalid payloads; all envelope types |

### Step 3 — EventEmitter

| Task | File | Done when |
|------|------|-----------|
| Typed `EventEmitter` with no Node.js dependency | `packages/sdk/src/events/EventEmitter.ts` | Works in browser, Node.js, React Native |
| Unit tests | `packages/sdk/tests/emitter.test.ts` | register, fire, remove, multiple listeners |

### Step 4 — Reconnect scheduler

| Task | File | Done when |
|------|------|-----------|
| `ReconnectScheduler` — delay sequence 1→2→5→10→30 s, capped | `packages/sdk/src/client/reconnect.ts` | Correct delays; `cancel()` stops further attempts |
| Unit tests | `packages/sdk/tests/reconnect.test.ts` | Delay sequence verified; cancel behaviour |

### Step 5 — `JiuwenSwarmClient`

| Task | File | Done when |
|------|------|-----------|
| `connect()` / `disconnect()` | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Opens WS; sends `connect` envelope; parses inbound envelopes; fires events |
| `send(message, options?)` | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Sends `chat` envelope; `token` events fire during streaming; `done` on finish |
| `sendEnvelope(type, payload)` | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Low-level serialised send |
| `tool_call` default rejection | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Auto-rejects with `{error:"not supported"}` unless `onToolCall` provided |
| `onToolCall` override | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Async callback returns result string or throws to send error back |
| Native WS / `ws` package detection | `packages/sdk/src/client/JiuwenSwarmClient.ts` | Uses native `WebSocket` if available; falls back to `ws` package; throws if neither |
| Unit tests | `packages/sdk/tests/client.test.ts` | connect, send, token/done events, tool_call rejection, reconnect on close |

### Step 6 — `SessionManager`

| Task | File | Done when |
|------|------|-----------|
| `list()`, `create()`, `setActive()`, `refresh()`, `active` getter | `packages/sdk/src/session/SessionManager.ts` | Sessions populated from `sessions` envelope; `active` persists across refresh |
| Unit tests | `packages/sdk/tests/session.test.ts` | all methods; active session persistence |

### Step 7 — Barrel export and docs

| Task | File | Done when |
|------|------|-----------|
| `src/index.ts` re-exports all public symbols | `packages/sdk/src/index.ts` | `import { JiuwenSwarmClient } from "@jiuwenswarm/sdk"` resolves in CJS and ESM |
| TypeDoc configuration | `packages/sdk/typedoc.json` | `npm run docs` generates HTML in `packages/sdk/docs/` without errors |

### Step 8 — npm publish

| Task | File | Done when |
|------|------|-----------|
| `publishConfig` in `package.json` | `packages/sdk/package.json` | `npm publish --dry-run` shows `dist/`, `README.md`, no `src/` |
| `README.md` in `packages/sdk/` | `packages/sdk/README.md` | Quick-start section with 3 code examples |
| Publish `0.1.0` | — | `npm install @jiuwenswarm/sdk` works from a fresh project |

**Phase 4 done when:** `npm install @jiuwenswarm/sdk` works; TypeScript examples in `examples/typescript/` run with `ts-node` against a local gateway; all vitest tests pass; TypeDoc generates without errors.

---

## Explicitly deferred (not planned for v1)

| Feature | Reason |
|---------|--------|
| Migrating browser extension to `@jiuwenswarm/sdk` | Extension works; migration is additive polish for v2 |
| Migrating mobile app to `@jiuwenswarm/sdk` | Same reason; protocol duplication is acceptable for v1 |
| Go / Rust / Java SDK | The REST gateway covers these languages adequately |
| SDK usage dashboard / analytics | Requires hosted mode |
| Rate limiting and per-token quotas in gateway | Requires hosted mode and multi-tenant auth |
| Webhooks (async result delivery) | Requires hosted mode; SSE is sufficient for v1 |
| MCP wrapper directly in Python SDK (without team runtime) | MCP is team-coordination only; not a priority for the direct SDK audience |

---

## Dependency order

```
Phase 2 system tests  ────────────────────────────── complete first
    │
    ├── Phase 2 advanced features (§6–§29)  ─────── can run in parallel with Phase 3
    │
    └── Phase 3 HTTP Gateway ──────────────────────
              │
              └── Phase 4 TypeScript SDK  ──────────
```
