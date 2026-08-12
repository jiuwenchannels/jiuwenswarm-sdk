# Roadmap

## Currently available

### Python SDK (`openjiuwen-sdk`)

**Core agent execution**
- `Agent.create()` — in-process agent backed by the JiuwenSwarm runtime
- `Agent.connect()` — remote agent connected via WebSocket envelope protocol
- `Agent.create_sync()` / `run_sync()` — sync wrappers for script use
- `agent.run(prompt)` — blocking, returns `AgentResult`
- `agent.stream(prompt)` — token-by-token via `AsyncIterator[str]`
- `agent.checkpoint()` / `Agent.restore()` — state persistence

**Configuration**
- `ModelConfig` — LLM provider, model, API key, temperature, max tokens, timeout
- `RemoteConfig` — server URL, auth token, timeout, retries
- Both support `from_env()` with documented env vars

**Session management**
- `Session.create()`, `list()`, `get()`, `delete()`
- `session.history()` — full `Message` list (role + text)
- Automatic session creation on first `agent.run()`
- Session reuse across multiple calls via `session_id=`

**Tools**
- `@tool` decorator — wraps sync and async Python functions
- Type annotation inference for all JSON schema types
- Optional parameters (default values → `required=False`)
- Custom `ToolParam` list for enum constraints
- `tool.to_tool_info()` — OpenAI-compatible function spec
- `tool.ainvoke()` / `invoke_sync()` — direct invocation

**Workflow (DAG orchestration)**
- `Workflow.create()` — named workflow with optional `ModelConfig`
- `add_node()` — `LLMNode`, `ToolNode`, `ConditionNode`
- `connect(src, dst)` — data-flow edges
- `branch(src, cond, true_target, false_target)` — conditional routing
- `workflow.run(inputs)` — returns `WorkflowResult`
- `workflow.stream(inputs)` — `AsyncIterator[dict]`
- `workflow.draw()` — Mermaid diagram string
- Cached compiled graph (recompile only on structural change)

**Multi-agent team**
- `Team.create(agents)` — assemble agents into a coordinated team
- `team.spawn(prompt)` — distribute work across team members
- `team.send(message, to=agent_name)` — targeted messaging

**A2A remote agent client**
- `RemoteAgent(url, agent_id)` — call any JiuwenSwarm agent over A2A protocol
- `remote_agent.run(prompt)` — returns `A2AResult`
- `remote_agent.stream(prompt)` — `AsyncIterator[str]`
- `remote_agent.cancel(task_id)` — cancel running task
- Context manager support

**Lifecycle hooks**
- `Hooks` container with six event slots
- Decorator form (`@hooks.token`, `@hooks.tool_call`, …)
- Constructor form (`Hooks(on_token=fn, …)`)
- Multiple callbacks per event, called in registration order
- `hooks.wire(emitter)` — binds to any `EventEmitter`
- `Agent.create(hooks=hooks)` — wired automatically

**EventEmitter**
- `on` / `off` / `off_all`
- Sync `emit` (schedules async callbacks on loop)
- Async `emit_async` (awaits all callbacks)

**Error hierarchy**
- `SdkError` base + ten specialised subclasses
- `ServerError` carries HTTP `status_code`

---

## Coming next

### Python SDK — advanced features

**Long-term memory** (`§6` in usage examples)
- `MemoryScope.USER` / `MemoryScope.SESSION`
- `memory.add(content, metadata)`, `memory.search(query)`
- Integration with `Agent.create(memory_scope=…)`

**Knowledge base and RAG** (`§7`)
- `KnowledgeBase.create(name, embedding_model)` — vector store management
- `kb.add_documents(docs)` — chunking, embedding, indexing
- `Retriever(kb, strategy="hybrid")` — BM25 + vector hybrid retrieval
- `Agent.create(knowledge_bases=[kb])` — automatic context injection

**SwarmFlow structured orchestration** (`§9`)
- `parallel(agents, prompt)` — fan-out to all agents simultaneously
- `pipeline(agents, prompt)` — chain where each output feeds next
- `phase(groups)` — multi-phase structured execution

**Evaluation framework** (`§10`)
- `MetricEvaluator` with pluggable metric classes
- `ExactMatchMetric`, `LLMAsJudgeMetric`, custom metrics
- Batch evaluation with scored results

**OpenTelemetry observability** (`§11`)
- `init_otel_tracer(service_name, endpoint)` — gRPC collector
- Automatic span creation for agent runs, tool calls, LLM calls

**Workspace facade** (`§12`)
- `Workspace(root=path)` — bind agent to a directory
- Sandbox mode — file/shell operations isolated to workspace
- `Agent.create(workspace=ws)` integration

**Checkpoint/restore — full integration** (`§13`)
- Registered backend adapters (SQLite, S3, Redis)
- `Agent.create(checkpoint_store="sqlite", checkpoint_every=5)`
- Cross-process restore via `Agent.restore(checkpoint_id)`

**Multimodal inputs** (`§14`)
- `ImageInput.from_file(path)`, `ImageInput.from_url(url)`
- `AudioInput.from_file(path)`
- `agent.run(prompt, images=[img], audio=[aud])`

**Multi-rollout** (`§15`)
- `MultiRolloutExecutor(agent, n=8)` — N parallel runs
- `executor.best_of(prompt, evaluator)` — ranked selection

**Task loop event hooks** (`§16`)
- `on_turn_start`, `on_tool_call`, `on_tool_result`, `on_llm_call`, `on_done`, `on_error`
- Tool-call interception with early return to block execution

**Sub-workflow composition** (`§18`)
- `SubWorkflowComponent` — embed one `Workflow` inside another
- Input/output schema mapping between parent and child

**Agent builder** (`§19`)
- `LlmAgentBuilder`, `WorkflowBuilder` — programmatic agent construction from spec

**Prompt builder** (`§20`)
- `MetaTemplateBuilder` — generate candidate prompts
- `FeedbackPromptBuilder` — refine using bad cases

**Custom store and checkpointer backends** (`§21`)
- `register_store(name, store_class)` — plug in `PostgresSessionStore`, etc.
- `register_checkpointer(name, class)` — plug in `S3Checkpointer`, etc.

**Security rails and permission engine** (`§22`)
- `PermissionEngine` with `PermissionsSection` allow/deny policies per tool
- Approval callbacks for human review before sensitive tool execution
- `Agent.create(permission_engine=pe)` integration

**LSP integration** (`§23`)
- `lsp.initialize_lsp(server_cmd)` — connect to any LSP (e.g., pyright, clangd)
- `get_lsp_tool()` — expose LSP diagnostics as an agent tool
- `get_pending_lsp_diagnostics()`, `shutdown_lsp()`

**Human-in-the-loop (HITT)** (`§24`)
- `TeamMemberSpec` with `TeamRole.HUMAN_AGENT`
- `enable_hitt=True` — team pauses at decision points for human approval
- Approval callbacks integrated into team coordination

**Agentic retrieval** (`§25`)
- `AgenticRetriever(base_retriever, llm)` — query rewriting + multi-round expansion
- LLM loop that iterates until retrieval confidence threshold is met

**Graph knowledge base** (`§26`)
- `GraphKnowledgeBase` — document parsing into subject-predicate-object triples
- Combined vector + graph traversal retrieval

**Context engine and compression** (`§27`)
- `ContextEngine` with pluggable processors
- `ToolResultBudgetProcessor`, `MessageSummaryOffloader`, `FullCompactProcessor`
- `Agent.create(context_engine=ce)` integration

**Online RL and trajectory collection** (`§28`)
- `OnlineRLOptimizer` with reward function registry
- `OfflineRLOptimizer` for batch training data collection
- Trajectory replay and export

**MCP server exposure** (`§29`)
- Expose JiuwenSwarm agents as MCP tools over stdio
- External MCP clients call JiuwenSwarm agents without knowing the runtime

---

### HTTP REST + WebSocket Gateway (Phase 3)

A standalone FastAPI server that exposes the JiuwenSwarm runtime over HTTP
and WebSocket. This enables cURL, browser fetch, and any language without a
native SDK.

**REST routes (`http://host:19001/v1/`)**

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Server status and version |
| GET | `/sessions` | List all sessions |
| POST | `/sessions` | Create session |
| GET | `/sessions/{id}` | Get session details |
| DELETE | `/sessions/{id}` | Delete session |
| POST | `/sessions/{id}/chat` | Blocking chat (returns full response) |
| POST | `/sessions/{id}/chat/stream` | SSE streaming chat |
| GET | `/agents` | List registered agents |
| POST | `/agents/{id}/run` | Run named agent (blocking) |
| POST | `/agents/{id}/stream` | Run named agent (SSE) |
| GET | `/tools` | List registered tools |
| POST | `/knowledge/{name}/documents` | Add documents to knowledge base |
| POST | `/knowledge/{name}/query` | Query knowledge base |
| POST | `/eval/batch` | Run evaluation batch |
| POST | `/agents/{id}/checkpoint` | Save checkpoint |
| GET | `/checkpoints` | List checkpoints |
| POST | `/checkpoints/{id}/restore` | Restore from checkpoint |

**WebSocket (`ws://host:19000/v1/ws`)**

Preserves the existing envelope protocol. Adds `protocol_version: "1"` to
`ack` payloads. Supports `client_type` in `connect` envelopes.

**Auth:** Bearer token middleware (optional in dev, enabled in prod).

---

### TypeScript / JavaScript SDK (Phase 4)

Published as `@jiuwenswarm/sdk` on npm. Connects to the HTTP gateway.

**Core client:**
- `JiuwenSwarmClient` — WebSocket connection with typed `EventEmitter`
- Auto-reconnect with exponential backoff: 1→2→5→10→30 seconds
- Runs in browser, Node.js, and React Native (no DOM dependency)

**Session management:**
- `SessionManager.list()`, `create()`, `setActive()`, `refresh()`

**Events:**
- `connected`, `disconnected`, `token`, `done`, `error`, `reconnecting`
- `tool_call` interception — handle geolocation, clipboard, etc. client-side

**React integration:**
- `useEffect` connection lifecycle
- `onToken` accumulator pattern for streaming output

**Distribution:**
- Dual CJS + ESM build
- Full TypeScript types
- Optional `ws` peer dependency (Node.js only; native WebSocket in browser)
- TypeDoc-generated API docs

---

## Dependency order

```
Python SDK core  ─────────────────────────────────────── available
    │
    ├── Python SDK advanced features (memory, RAG, HITT, etc.)
    │
    └── HTTP Gateway ─────────────────────────────────── Phase 3
              │
              └── TypeScript SDK ───────────────────────── Phase 4
```
