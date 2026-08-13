# Examples

Runnable examples covering every aspect of the SDK.
The examples mirror the sections in the official usage guide.

## Prerequisites

```bash
pip install openjiuwen-sdk[runtime]   # in-process Python examples
pip install openjiuwen-sdk            # remote / A2A examples only
pip install httpx                     # streaming REST example in §4
```

Set at least one environment variable before running:

```bash
export JIUWENSWARM_API_KEY=sk-your-openai-key
# or
export OPENAI_API_KEY=sk-your-openai-key
```

For TypeScript examples:
```bash
npm install @jiuwenswarm/sdk
```

For REST / cURL examples, start the HTTP gateway first:
```bash
jiuwenswarm serve   # listens on ws://localhost:19000 and http://localhost:19001
```

---

## Python SDK examples

| File | §  | Feature |
|------|----|---------|
| `quick_start.py` | §0–1 | 10-line hello world — in-process and remote mode |
| `streaming.py` | §2 | Stream tokens with async-for and event callbacks |
| `session_management.py` | §3 | Session CRUD, multi-turn conversation, history |
| `custom_tools.py` | §4 | `@tool` decorator — sync, async, enum constraints |
| `05_workflow_advanced.py` | §5 | Full workflow DAG with Start/End/LLM/Branch/Loop nodes |
| `06_long_term_memory.py` | §6 | Long-term memory scopes, `add`, `search`, `delete` |
| `07_knowledge_base_rag.py` | §7 | Knowledge base creation, document ingestion, RAG retrieval |
| `multi_agent_team.py` | §8 | Three-agent team — researcher, writer, reviewer |
| `09_swarmflow.py` | §9 | SwarmFlow — `parallel()`, `pipeline()`, `phase()` |
| `10_evaluation.py` | §10 | EvalCase, ExactMatchMetric, LLMAsJudgeMetric, custom metrics |
| `11_observability.py` | §11 | OpenTelemetry tracing with `init_otel_tracer` |
| `12_workspace.py` | §12 | Workspace diff, modified-file tracking, sandbox mode |
| `13_checkpoint_restore.py` | §13 | `checkpoint()`, `Agent.restore()`, periodic checkpointing |
| `14_multimodal.py` | §14 | `ImageInput`, `AudioInput`, vision and audio model configs |
| `15_multi_rollout.py` | §15 | `MultiRolloutExecutor`, `best_of()`, parallel rollouts |
| `16_task_loop_hooks.py` | §16 | `TaskLoopEventHandler` full lifecycle, `ToolGuard` |
| `hooks_lifecycle.py` | §16 | `Hooks` in decorator and constructor form |
| `17_a2a_server_and_client.py` | §17 | A2A server side + `RemoteAgent` client + team composition |
| `a2a_remote_agent.py` | §17 | A2A client — run, stream, cancel, local+remote composition |
| `18_sub_workflow.py` | §18 | `SubWorkflowComponent`, input/output mapping |
| `19_agent_builder.py` | §19 | `LlmAgentBuilder` fluent API, `WorkflowBuilder` |
| `20_prompt_builder.py` | §20 | `MetaTemplateBuilder`, `FeedbackPromptBuilder.refine()` |
| `21_custom_backends.py` | §21 | `PostgresSessionStore`, `S3Checkpointer`, `register_store` |
| `22_security_rails.py` | §22 | `PermissionEngine`, `PermissionsSection`, `CLIApprovalHost` |
| `23_lsp_integration.py` | §23 | LSP initialize, diagnostics, code actions |
| `24_hitt.py` | §24 | Human-in-the-team (`TeamRole.HUMAN_AGENT`, HITT protocol) |
| `25_agentic_retrieval.py` | §25 | `AgenticRetriever` — iterative multi-round retrieval |
| `26_graph_knowledge_base.py` | §26 | `GraphKnowledgeBase` — triple extraction, graph queries |
| `27_context_engine.py` | §27 | `ContextEngine` processors: budget, summary, compact |
| `28_online_rl.py` | §28 | `OnlineRLOptimizer`, `OfflineRLOptimizer`, reward registry |
| `29_mcp_server.py` | §29 | MCP server — subprocess and embedded `build_server()` modes |
| `workflow_dag.py` | — | Workflow DAG — linear, conditional branch, streaming |

---

## TypeScript SDK examples

Located in `typescript/`.
Require the HTTP gateway (`jiuwenswarm serve`) running at `ws://localhost:19000`.

| File | §  | Feature |
|------|----|---------|
| `typescript/01_connect_and_chat.ts` | §1 | Connect via WebSocket and send a chat message |
| `typescript/02_session_management.ts` | §2 | List, resume, and create sessions |
| `typescript/03_streaming_react.tsx` | §3 | React component with streaming token output |
| `typescript/04_knowledge_base_rest.ts` | §4 | Knowledge base query via `fetch` + context injection |
| `typescript/05_reconnect_handling.ts` | §5 | Automatic exponential-back-off and manual reconnect |
| `typescript/06_tool_call_interception.ts` | §6 | Client-side tool execution (Geolocation, clipboard) |

---

## REST / cURL examples

Located in `rest/`.
Require the HTTP gateway (`jiuwenswarm serve`) running at `http://localhost:19001`.

| File | §  | Feature |
|------|----|---------|
| `rest/01_health_check.sh` | §1 | Health probe |
| `rest/02_sessions.sh` | §2 | Session list, create, get, delete |
| `rest/03_blocking_chat.sh` | §3 | Blocking chat — full response in one call |
| `rest/04_streaming_chat_sse.sh` | §4 | Streaming chat via SSE (+ Python httpx example) |
| `rest/05_agents_and_tools.sh` | §5 | List agents, run agent, list tools |
| `rest/06_knowledge_base.sh` | §6 | Create KB, add documents, query |
| `rest/07_eval_batch.sh` | §7 | Evaluation batch with metric scores |
| `rest/08_agent_streaming_sse.sh` | §8 | Agent streaming SSE (+ Go example) |
| `rest/09_checkpoint_restore.sh` | §9 | Create checkpoint, list, restore, continue |

---

## Running examples

```bash
# Python
python examples/quick_start.py
python examples/05_workflow_advanced.py

# TypeScript (requires ts-node or ESM runner)
npx ts-node examples/typescript/01_connect_and_chat.ts

# Shell / cURL (requires gateway running)
bash examples/rest/01_health_check.sh
```
