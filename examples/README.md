# Examples

Runnable examples covering every aspect of the SDK.
The examples mirror the sections in the official usage guide.

```
examples/
├── python/          Python SDK examples (§0–§29)
├── typescript/      TypeScript SDK examples (§1–§6)
└── rest/            REST / cURL shell scripts (§1–§9)
```

## Prerequisites

**Python**
```bash
pip install openjiuwen-sdk[runtime]   # in-process examples
pip install openjiuwen-sdk            # remote / A2A examples only
pip install httpx                     # used in rest/04 Python snippet
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

| File | §  | Feature |
|------|----|---------|
| `python/01_quick_start.py` | §0–1 | 10-line hello world — in-process and remote mode |
| `python/02_streaming.py` | §2 | Stream tokens with async-for and event callbacks |
| `python/03_session_management.py` | §3 | Session CRUD, multi-turn conversation, history |
| `python/04_custom_tools.py` | §4 | `@tool` decorator — sync, async, enum constraints |
| `python/05_workflow_advanced.py` | §5 | Full workflow DAG with Start/End/LLM/Branch/Loop nodes |
| `python/05b_workflow_basic.py` | §5 | Workflow DAG — linear, conditional, streaming (simple variant) |
| `python/06_long_term_memory.py` | §6 | Long-term memory scopes, `add`, `search`, `delete` |
| `python/07_knowledge_base_rag.py` | §7 | Knowledge base creation, document ingestion, RAG retrieval |
| `python/08_multi_agent_team.py` | §8 | Three-agent team — researcher, writer, reviewer |
| `python/09_swarmflow.py` | §9 | SwarmFlow — `parallel()`, `pipeline()`, `phase()` |
| `python/10_evaluation.py` | §10 | EvalCase, ExactMatchMetric, LLMAsJudgeMetric, custom metrics |
| `python/11_observability.py` | §11 | OpenTelemetry tracing with `init_otel_tracer` |
| `python/12_workspace.py` | §12 | Workspace diff, modified-file tracking, sandbox mode |
| `python/13_checkpoint_restore.py` | §13 | `checkpoint()`, `Agent.restore()`, periodic checkpointing |
| `python/14_multimodal.py` | §14 | `ImageInput`, `AudioInput`, vision and audio model configs |
| `python/15_multi_rollout.py` | §15 | `MultiRolloutExecutor`, `best_of()`, parallel rollouts |
| `python/16_task_loop_hooks.py` | §16 | `TaskLoopEventHandler` full lifecycle, `ToolGuard` |
| `python/16b_hooks_simple.py` | §16 | `Hooks` in decorator and constructor form (simple variant) |
| `python/17_a2a_server_and_client.py` | §17 | A2A server side + `RemoteAgent` client + team composition |
| `python/17b_a2a_client_only.py` | §17 | A2A client — run, stream, cancel (simple variant) |
| `python/18_sub_workflow.py` | §18 | `SubWorkflowComponent`, input/output mapping |
| `python/19_agent_builder.py` | §19 | `LlmAgentBuilder` fluent API, `WorkflowBuilder` |
| `python/20_prompt_builder.py` | §20 | `MetaTemplateBuilder`, `FeedbackPromptBuilder.refine()` |
| `python/21_custom_backends.py` | §21 | `PostgresSessionStore`, `S3Checkpointer`, `register_store` |
| `python/22_security_rails.py` | §22 | `PermissionEngine`, `PermissionsSection`, `CLIApprovalHost` |
| `python/23_lsp_integration.py` | §23 | LSP initialize, diagnostics, code actions |
| `python/24_hitt.py` | §24 | Human-in-the-team (`TeamRole.HUMAN_AGENT`, HITT protocol) |
| `python/25_agentic_retrieval.py` | §25 | `AgenticRetriever` — iterative multi-round retrieval |
| `python/26_graph_knowledge_base.py` | §26 | `GraphKnowledgeBase` — triple extraction, graph queries |
| `python/27_context_engine.py` | §27 | `ContextEngine` processors: budget, summary, compact |
| `python/28_online_rl.py` | §28 | `OnlineRLOptimizer`, `OfflineRLOptimizer`, reward registry |
| `python/29_mcp_server.py` | §29 | MCP server — subprocess and embedded `build_server()` modes |
| `python/30_gateway_startup.py` | §30 | HTTP + WebSocket gateway — start server, REST chat, SSE stream, WS protocol |

---

## TypeScript SDK (`typescript/`)

Require the HTTP gateway (`jiuwenswarm serve`) at `ws://localhost:19000`.

| File | §  | Feature |
|------|----|---------|
| `typescript/01_connect_and_chat.ts` | §1 | Connect via WebSocket and send a chat message |
| `typescript/02_session_management.ts` | §2 | List, resume, and create sessions |
| `typescript/03_streaming_react.tsx` | §3 | React component with streaming token output |
| `typescript/04_knowledge_base_rest.ts` | §4 | Knowledge base query via `fetch` + context injection |
| `typescript/05_reconnect_handling.ts` | §5 | Automatic exponential back-off and manual reconnect |
| `typescript/06_tool_call_interception.ts` | §6 | Client-side tool execution (Geolocation, clipboard) |

---

## REST / cURL (`rest/`)

Require the HTTP gateway (`jiuwenswarm serve`) at `http://localhost:19001`.

| File | §  | Feature |
|------|----|---------|
| `rest/01_health_check.sh` | §1 | Health probe |
| `rest/02_sessions.sh` | §2 | Session list, create, get, delete |
| `rest/03_blocking_chat.sh` | §3 | Blocking chat — full response in one call |
| `rest/04_streaming_chat_sse.sh` | §4 | Streaming chat via SSE (+ Python httpx snippet) |
| `rest/05_agents_and_tools.sh` | §5 | List agents, run agent, list tools |
| `rest/06_knowledge_base.sh` | §6 | Create KB, add documents, query |
| `rest/07_eval_batch.sh` | §7 | Evaluation batch with metric scores |
| `rest/08_agent_streaming_sse.sh` | §8 | Agent streaming SSE (+ Go snippet) |
| `rest/09_checkpoint_restore.sh` | §9 | Create checkpoint, list, restore, continue |

---

## Running examples

```bash
# Python
python examples/python/01_quick_start.py
python examples/python/05_workflow_advanced.py

# TypeScript (requires ts-node or an ESM runner)
npx ts-node examples/typescript/01_connect_and_chat.ts

# Shell / cURL (requires gateway running)
bash examples/rest/01_health_check.sh
```
