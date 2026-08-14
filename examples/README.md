# Examples

Runnable examples covering every aspect of the SDK, organised by topic.

```
examples/
├── python/
│   ├── core/              Agent basics, streaming, sessions, tools
│   ├── agents/            Multi-agent teams, swarm, A2A, stream events
│   ├── workflow/          Workflow DAG, sub-workflows
│   ├── memory/            Long-term memory, RAG, agentic and graph retrieval
│   ├── optimization/      Evaluation, rollouts, HITL, online RL
│   ├── observability/     OTel tracing, checkpoints
│   ├── workspace/         Workspace sandbox and diff
│   ├── infra/             Prompt builder, backends, security, LSP, MCP, gateway
│   └── advanced/          Multimodal, task-loop hooks, agent builder
├── typescript/            TypeScript SDK examples (requires gateway)
└── rest/                  REST / cURL shell scripts (requires gateway)
```

## Prerequisites

**Python**
```bash
pip install openjiuwen-sdk[runtime]   # in-process examples (core/, agents/, workflow/, memory/, optimization/, advanced/)
pip install openjiuwen-sdk            # remote / gateway examples (infra/, A2A)
pip install httpx                     # used in rest/ Python snippet
```

Set at least one environment variable:
```bash
export JIUWENSWARM_API_KEY=sk-your-openai-key
# or
export OPENAI_API_KEY=sk-your-openai-key
```

**TypeScript**
```bash
npm install @jiuwenswarm/sdk
```

**REST / cURL** — start the HTTP gateway first:
```bash
jiuwenswarm serve   # ws://localhost:19000  and  http://localhost:19001
```

---

## Python SDK (`python/`)

### `core/` — Agent basics

| File | Feature |
|------|---------|
| `core/quick_start.py` | 10-line hello world — in-process and remote mode |
| `core/streaming.py` | Stream tokens — async-for, event callbacks, and typed `stream_events()` |
| `core/session_management.py` | Session CRUD, multi-turn conversation, history |
| `core/custom_tools.py` | `@tool` decorator — sync, async, enum constraints |

### `agents/` — Multi-agent coordination

| File | Feature |
|------|---------|
| `agents/multi_agent_team.py` | Three-agent team — researcher, writer, reviewer |
| `agents/swarmflow.py` | SwarmFlow — `parallel()`, `pipeline()`, `phase()` |
| `agents/a2a_server_and_client.py` | A2A server side + `RemoteAgent` client + team composition |
| `agents/a2a_client_only.py` | A2A client — run, stream, cancel (simple variant) |
| `agents/stream_events.py` | Typed `stream_events()` — all event types, `AgentMode`, `ChannelId`, `context_prefix`, cancellation |
| `agents/team_stream.py` | `team.stream()` — watch multi-agent coordination in real time with `TeamEvent` |

### `workflow/` — Workflow DAG

| File | Feature |
|------|---------|
| `workflow/advanced.py` | Full workflow DAG with Start/End/LLM/Branch/Loop nodes |
| `workflow/basic.py` | Workflow DAG — linear, conditional, streaming (simple variant) |
| `workflow/sub_workflow.py` | `SubWorkflowComponent`, input/output mapping |

### `memory/` — Memory and knowledge

| File | Feature |
|------|---------|
| `memory/long_term_memory.py` | Long-term memory scopes, `add`, `search`, `delete` |
| `memory/knowledge_base_rag.py` | Knowledge base creation, document ingestion, RAG retrieval |
| `memory/agentic_retrieval.py` | `AgenticRetriever` — iterative multi-round retrieval |
| `memory/graph_knowledge_base.py` | `GraphKnowledgeBase` — triple extraction, graph queries |

### `optimization/` — Evaluation and reinforcement learning

| File | Feature |
|------|---------|
| `optimization/evaluation.py` | `EvalCase`, `ExactMatchMetric`, `LLMAsJudgeMetric`, custom metrics |
| `optimization/multi_rollout.py` | `MultiRolloutExecutor`, `best_of()`, parallel rollouts |
| `optimization/hitt.py` | Human-in-the-team (`TeamRole.HUMAN_AGENT`, HITT protocol) |
| `optimization/online_rl.py` | `OnlineRLOptimizer`, `OfflineRLOptimizer`, reward registry |

### `observability/` — Tracing and checkpoints

| File | Feature |
|------|---------|
| `observability/otel_tracing.py` | OpenTelemetry tracing with `init_otel_tracer` |
| `observability/checkpoint_restore.py` | `checkpoint()`, `Agent.restore()`, periodic checkpointing |

### `workspace/` — Workspace sandbox

| File | Feature |
|------|---------|
| `workspace/sandbox_and_diff.py` | Workspace diff, modified-file tracking, sandbox mode |

### `infra/` — Infrastructure and integrations

| File | Feature |
|------|---------|
| `infra/prompt_builder.py` | `MetaTemplateBuilder`, `FeedbackPromptBuilder.refine()` |
| `infra/custom_backends.py` | `PostgresSessionStore`, `S3Checkpointer`, `register_store` |
| `infra/security_rails.py` | `PermissionEngine`, `PermissionsSection`, `CLIApprovalHost` |
| `infra/lsp_integration.py` | LSP initialize, diagnostics, code actions |
| `infra/context_engine.py` | `ContextEngine` processors: budget, summary, compact |
| `infra/mcp_server.py` | MCP server — subprocess and embedded `build_server()` modes |
| `infra/gateway_startup.py` | HTTP + WebSocket gateway — start server, REST chat, SSE stream, WS protocol |

### `advanced/` — Advanced features

| File | Feature |
|------|---------|
| `advanced/multimodal.py` | `ImageInput`, `AudioInput`, vision and audio model configs |
| `advanced/task_loop_hooks.py` | `TaskLoopEventHandler` full lifecycle, `ToolGuard` |
| `advanced/hooks_simple.py` | `Hooks` in decorator and constructor form (simple variant) |
| `advanced/agent_builder.py` | `LlmAgentBuilder` fluent API, `WorkflowBuilder` |

---

## TypeScript SDK (`typescript/`)

Require the HTTP gateway (`jiuwenswarm serve`) at `ws://localhost:19000`.

| File | Feature |
|------|---------|
| `typescript/01_connect_and_chat.ts` | Connect via WebSocket and send a chat message |
| `typescript/02_session_management.ts` | List, resume, and create sessions |
| `typescript/03_streaming_react.tsx` | React component with streaming token output |
| `typescript/04_knowledge_base_rest.ts` | Knowledge base query via `fetch` + context injection |
| `typescript/05_reconnect_handling.ts` | Automatic exponential back-off and manual reconnect |
| `typescript/06_tool_call_interception.ts` | Client-side tool execution (Geolocation, clipboard) |

---

## REST / cURL (`rest/`)

Require the HTTP gateway (`jiuwenswarm serve`) at `http://localhost:19001`.

| File | Feature |
|------|---------|
| `rest/01_health_check.sh` | Health probe |
| `rest/02_sessions.sh` | Session list, create, get, delete |
| `rest/03_blocking_chat.sh` | Blocking chat — full response in one call |
| `rest/04_streaming_chat_sse.sh` | Streaming chat via SSE (+ Python httpx snippet) |
| `rest/05_agents_and_tools.sh` | List agents, run agent, list tools |
| `rest/06_knowledge_base.sh` | Create KB, add documents, query |
| `rest/07_eval_batch.sh` | Evaluation batch with metric scores |
| `rest/08_agent_streaming_sse.sh` | Agent streaming SSE (+ Go snippet) |
| `rest/09_checkpoint_restore.sh` | Create checkpoint, list, restore, continue |

---

## Running examples

```bash
# Python — run from the repo root
python examples/python/core/quick_start.py
python examples/python/agents/stream_events.py
python examples/python/workflow/advanced.py
python examples/python/memory/knowledge_base_rag.py
python examples/python/optimization/evaluation.py
python examples/python/infra/gateway_startup.py

# TypeScript (requires ts-node or an ESM runner)
npx ts-node examples/typescript/connect_and_chat.ts

# Shell / cURL (requires gateway running)
bash examples/rest/health_check.sh
```
