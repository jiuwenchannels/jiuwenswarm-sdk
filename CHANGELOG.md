# Changelog

All notable changes to `openjiuwen-sdk` and `@jiuwenswarm/sdk` are documented here.
Versions follow [Semantic Versioning](https://semver.org/).

---

## [1.0.0]

First stable release. Covers all four phases of the original development plan.

### Python SDK (`openjiuwen-sdk`)

**Core agent execution**
- `Agent.create()` — in-process agent backed by `openjiuwen.core` runtime
- `Agent.connect()` — remote agent connected via WebSocket or REST
- `agent.run()` — blocking execution returning `AgentResult`
- `agent.stream()` — token-by-token `AsyncIterator[str]`
- `agent.run_sync()` — sync wrapper for scripts
- `agent.checkpoint()` / `Agent.restore()` — opaque checkpoint ID

**Configuration**
- `ModelConfig` — LLM provider, model, API key, temperature, timeout, retries
- `RemoteConfig` — server URL, auth token, timeout, retries
- `SdkConfig` — combined wrapper with `from_env()`
- All env vars documented in `docs/configuration.md`

**Session management**
- `Session.create()`, `list()`, `get()`, `delete()`, `history()`
- `Message` frozen dataclass with role, text, timestamp
- Automatic session creation on first `run()`

**Tools**
- `@tool` decorator — sync and async Python functions
- Full JSON-schema type inference from annotations
- Optional parameters via default values
- Enum constraints via `ToolParam`
- `tool.to_tool_info()` — OpenAI-compatible spec
- `tool.ainvoke()` / `invoke_sync()` — direct invocation

**Workflow (DAG orchestration)**
- `Workflow.create()`, `add_node()`, `connect()`, `branch()`
- `LLMNode`, `ToolNode`, `ConditionNode`, `SubWorkflowComponent`
- `workflow.run()`, `workflow.stream()`, `workflow.draw()` (Mermaid)
- Cached compiled graph

**Multi-agent team**
- `Team.create()`, `team.spawn()`, `team.send()`, `team.status()`
- `TeamResult`, `TeamStatus` frozen dataclasses

**A2A remote agent client**
- `RemoteAgent(url, agent_id)` — A2A protocol client
- `remote.run()`, `remote.stream()`, `remote.cancel()`, `remote.close()`
- Context manager support

**Lifecycle hooks**
- `Hooks` container — six event slots, decorator and constructor form
- `hooks.wire(emitter)` — binds to any `EventEmitter`
- `Agent.create(hooks=hooks)`

**TaskLoopEventHandler**
- All lifecycle methods: `on_turn_start`, `on_tool_call`, `on_tool_result`, `on_llm_call`, `on_done`, `on_error`
- Tool-call interception via early `ToolResult` return
- `ToolGuard` — raise `ToolError` for tools not in allow-list

**Long-term memory**
- `MemoryScope.USER` / `.SESSION` / `.GLOBAL`
- `memory.add()`, `memory.search()`, `memory.delete()`, `memory.list()`
- `Agent.create(memory_scope=MemoryScope.USER)`

**Knowledge base and RAG**
- `KnowledgeBase.create()` — vector store management
- `kb.add_documents()` — chunking, embedding, indexing
- `Retriever(kb, strategy="hybrid")` — BM25 + vector hybrid retrieval
- `AgenticRetriever` — multi-round query rewriting with LLM loop
- `GraphKnowledgeBase` — triple extraction, combined vector+graph retrieval
- `Agent.create(knowledge_bases=[kb])`

**SwarmFlow structured orchestration**
- `parallel(agents, prompt)`, `pipeline(agents, prompt)`, `phase(groups)`
- `run_swarmflow(spec, prompt=...)`

**Evaluation framework**
- `EvalCase`, `MetricEvaluator`
- `ExactMatchMetric`, `LLMAsJudgeMetric`, custom `Metric` protocol
- Batch evaluation with per-case scores and summary

**OpenTelemetry observability**
- `init_otel_tracer(config)` — gRPC OTLP exporter
- Automatic spans for agent runs, tool calls, LLM calls

**Workspace**
- `Workspace(root, sandbox=False)` — bind agent to a directory
- `workspace.diff()`, `workspace.modified_files`
- `Agent.create(workspace=ws)`

**Checkpoint/restore — backend registry**
- `SessionStore` and `CheckpointerBackend` protocols
- `register_store()`, `register_checkpointer()`
- Built-in: `SqliteSessionStore`, `SqliteCheckpointer`
- Contrib: `PostgresSessionStore`, `S3Checkpointer`
- `Agent.create(checkpoint_store="sqlite", checkpoint_every=5)`

**Multimodal inputs**
- `ImageInput.from_file()`, `ImageInput.from_url()`
- `AudioInput.from_file()`
- `agent.run(prompt, images=[img], audio=[aud])`

**Multi-rollout**
- `MultiRolloutExecutor(agent, config)`
- `executor.run(prompt)` → `list[AgentResult]`
- `executor.best_of(prompt, evaluator)` → `AgentResult`

**Security rails**
- `PermissionEngine` with `PermissionsSection` allow/deny/ask policies
- `CLIApprovalHost` — stdout y/n approval
- `ApprovalHost` protocol for custom approval UIs
- `Agent.create(permission_engine=pe)`

**LSP integration**
- `lsp.initialize_lsp(server_cmd)` — any LSP over stdio
- `lsp.get_lsp_tool()` — expose diagnostics as agent tool
- `lsp.get_pending_lsp_diagnostics()`, `lsp.shutdown_lsp()`

**Human-in-the-loop (HITT)**
- `TeamRole.HUMAN_AGENT`, `TeamMemberSpec` with async callback
- `Team.create(enable_hitt=True)` — pause at decision points

**Context engine**
- `ContextEngine` with pluggable processors
- `ToolResultBudgetProcessor`, `MessageSummaryOffloader`, `FullCompactProcessor`, `MicroCompactProcessor`
- `engine.last_stats` — before/after token counts
- `Agent.create(context_engine=ce)`

**Online RL and trajectory collection**
- `RLConfig`, `RewardRegistry`, `RolloutWithReward`
- `OnlineRLOptimizer` — records reward per run, applies policy updates
- `OfflineRLOptimizer` — JSONL trajectory export
- `Agent.create(rl_optimizer=optimizer)`

**MCP server exposure**
- `python -m openjiuwen.agent_teams.mcp` — subprocess stdio mode
- `build_server()` — embedded async mode with `mcp.server.stdio`

**Agent builder**
- `LlmAgentBuilder` fluent API — `.with_name()`, `.with_model()`, `.with_tools()`, `.with_memory()`, `.build()`
- `WorkflowBuilder` — `.add_step()`, `.branch()`, `.build()`

**Prompt builder**
- `MetaTemplateBuilder(agent, n)` — generate N candidate prompts
- `FeedbackPromptBuilder(agent)` — `.refine(prompt, bad_cases)`

**Custom backends (contrib)**
- `PostgresSessionStore` — asyncpg
- `S3Checkpointer` — aiobotocore

**EventEmitter**
- `on`, `off`, `off_all`, `emit`, `emit_async`

**Error hierarchy**
- `SdkError` + 10 specialised subclasses

---

### HTTP + WebSocket Gateway (`openjiuwen.gateway`)

- `build_gateway_app(config: GatewayConfig)` → FastAPI app
- `python -m openjiuwen.gateway` — standalone server entrypoint
- Bearer token auth middleware (optional in dev)
- 19 REST routes under `/v1/` (sessions, chat, agents, tools, knowledge, eval, checkpoints)
- SSE streaming for `/chat/stream` and `/agents/{id}/stream`
- WebSocket at `/v1/ws` — full envelope protocol v1
- A2A routes at `/a2a/` (coexist with REST)
- OpenAPI spec auto-generated at `/docs` and `/openapi.json`
- CORS configuration via `GatewayConfig.cors_origins`

---

### TypeScript SDK (`@jiuwenswarm/sdk`)

- `JiuwenSwarmClient` — WebSocket client with typed `EventEmitter`
- Auto-reconnect: exponential back-off 1→2→5→10→30 s, capped
- `SessionManager` — `list()`, `create()`, `setActive()`, `refresh()`, `active`
- Events: `connected`, `disconnected`, `token`, `done`, `error`, `reconnecting`
- `onToolCall` — intercept and handle tool calls client-side
- Browser, Node.js, and React Native support
- `ws` optional peer dependency for Node.js
- Dual CJS + ESM build with full TypeScript types
- Published as `@jiuwenswarm/sdk` on npm
