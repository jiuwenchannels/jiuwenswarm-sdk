# JiuwenSwarm SDK

Three SDKs, one runtime. Build and deploy AI agents in Python, TypeScript,
or via plain HTTP — all sharing the same server backend.

```python
from openjiuwen.sdk import Agent, ModelConfig

agent = await Agent.create("researcher", model=ModelConfig.from_env())
result = await agent.run("Explain the CAP theorem in one paragraph.")
print(result.text)
```

---

## What is in this repository

| Package | Language | Install |
|---------|----------|---------|
| **`openjiuwen-sdk`** | Python 3.11+ | `pip install openjiuwen-sdk` |
| **`@jiuwenswarm/sdk`** | TypeScript / JavaScript | `npm install @jiuwenswarm/sdk` |
| **REST + WebSocket gateway** | Any language via curl | `python -m openjiuwen.gateway` |

All three target the same server runtime (`openjiuwen.core` +
`openjiuwen.harness`). The gateway speaks HTTP/WebSocket so any language
that can make an HTTP call can reach JiuwenSwarm.

---

## Quick starts

### Python — in-process

The runtime runs inside your Python process. Full access to checkpoints,
workspaces, event handlers, and custom backends.

```python
import asyncio
from openjiuwen.sdk import Agent, ModelConfig

async def main():
    agent = await Agent.create(
        "planner",
        model=ModelConfig(provider="openai", model="gpt-4o"),
    )
    async for token in agent.stream("Plan a three-day trip to Kyoto."):
        print(token, end="", flush=True)

asyncio.run(main())
```

### Python — remote

The runtime runs in a separate JiuwenSwarm server process. Connect over
WebSocket and use the same API.

```python
from openjiuwen.sdk import Agent

agent = await Agent.connect("wss://prod.example.com:19000/v1/ws", auth_token="tok")
result = await agent.run("Summarise the attached report.")
```

### TypeScript / JavaScript

```typescript
import { JiuwenSwarmClient } from "@jiuwenswarm/sdk";

const client = new JiuwenSwarmClient({
  url: "ws://localhost:19000/v1/ws",
  onToken: (text) => process.stdout.write(text),
  onDone: (sessionId) => console.log("done", sessionId),
});

await client.connect();
client.send("What is the capital of France?");
```

### REST / curl

```bash
# Start a session
SESSION=$(curl -s -X POST http://localhost:19001/v1/sessions \
  -H "Content-Type: application/json" \
  -d '{"title":"demo"}' | jq -r .session_id)

# Stream a response
curl -N -X POST http://localhost:19001/v1/sessions/$SESSION/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"message":"What is quantum entanglement?"}'
```

---

## Installation

### Python SDK

```bash
pip install openjiuwen-sdk                     # remote mode only (Agent.connect)
pip install "openjiuwen-sdk[runtime]"          # + in-process runtime (Agent.create)
pip install "openjiuwen-sdk[otel]"             # + OpenTelemetry tracing
pip install "openjiuwen-sdk[redis]"            # + Redis checkpoint backend
pip install "openjiuwen-sdk[all]"              # everything
```

### TypeScript SDK

```bash
npm install @jiuwenswarm/sdk        # browser and React Native
npm install @jiuwenswarm/sdk ws     # Node.js (ws is an optional peer dependency)
```

### Gateway server

```bash
pip install "openjiuwen-sdk[runtime]"
python -m openjiuwen.gateway --port-rest 19001 --port-ws 19000
```

---

## Python SDK — features

### Agent

```python
from openjiuwen.sdk import Agent, ModelConfig

agent  = await Agent.create("name", model=ModelConfig.from_env())
result = await agent.run("prompt")         # → AgentResult
stream = agent.stream("prompt")           # → AsyncIterator[str]
ckpt   = await agent.checkpoint()         # → str (checkpoint id)
agent2 = await Agent.restore(ckpt)        # recreate from checkpoint
agent.run_sync("prompt")                  # sync variant
```

### Session

```python
from openjiuwen.sdk import Session

session  = await Session.create("My chat")
sessions = await Session.list()
s        = await Session.get(session.session_id)
messages = await s.history()
await s.delete()
```

### Tools

```python
from openjiuwen.sdk import tool, ToolParam

@tool(name="web_search", description="Search the web.")
async def web_search(query: str, num_results: int = 5) -> str:
    ...

agent = await Agent.create("researcher", tools=[web_search])
```

### Workflow (DAG)

```python
from openjiuwen.sdk import Workflow, AgentNode, TransformNode

wf = Workflow.create("pipeline")
wf.add_node("fetch", AgentNode(agent=fetcher, prompt_key="url"))
wf.add_node("clean", TransformNode(fn=clean_html))
wf.add_node("summarise", AgentNode(agent=summariser, prompt_key="text"))
wf.connect("fetch", "clean")
wf.connect("clean", "summarise")

result = await wf.run({"url": "https://example.com"})
```

### Multi-agent team

```python
from openjiuwen.sdk import Team

team = await Team.create([researcher, analyst, writer])
result = await team.spawn("Research and write a report on LLM safety.")
```

### Lifecycle hooks

```python
from openjiuwen.sdk import Hooks

hooks = Hooks()

@hooks.token
async def on_token(token: str) -> None:
    print(token, end="", flush=True)

@hooks.tool_call
async def on_tool(name: str, args: dict) -> None:
    print(f"→ {name}({args})")

agent = await Agent.create("coder", hooks=hooks)
```

### Memory and knowledge

```python
from openjiuwen.sdk import Memory, KnowledgeBase, AgenticRetriever

memory = Memory.create(agent)
await memory.add("User prefers concise answers.")

kb = await KnowledgeBase.create("docs")
await kb.add_documents(["Document A…", "Document B…"])
retriever = AgenticRetriever(kb)
chunks = await retriever.retrieve("quantum computing", max_hops=2)
```

### Evaluation

```python
from openjiuwen.sdk import Evaluator, ExactMatchMetric, LLMAsJudgeMetric

evaluator = Evaluator(metrics=[ExactMatchMetric(), LLMAsJudgeMetric(judge_model=cfg)])
result = await evaluator.run(cases)
print(result.score)
```

### OpenTelemetry tracing

```python
from openjiuwen.sdk import OtelTracer, OtelTracerConfig

tracer = OtelTracer(OtelTracerConfig(service_name="my-app"))
tracer.instrument(agent)
```

### Remote agent (A2A)

```python
from openjiuwen.sdk import RemoteAgent

remote = RemoteAgent("https://partner.example.com", agent_id="analyst")
result = await remote.run("Analyse Q3 revenue data.")
```

### Online RL

```python
from openjiuwen.sdk import OnlineRL, RLConfig

rl = OnlineRL(agent, RLConfig(algorithm="ppo", lr=1e-4))
await rl.step("Generate a concise summary.", reward_fn=my_reward)
```

### Full feature list

| Module | Key classes |
|--------|-------------|
| `sdk.agent` | `Agent`, `AgentResult` |
| `sdk.session` | `Session`, `SessionInfo`, `ChatMessage` |
| `sdk.tools` | `@tool`, `ToolParam` |
| `sdk.workflow` | `Workflow`, `AgentNode`, `TransformNode`, `BranchNode`, `SubWorkflowNode`, `WorkflowResult` |
| `sdk.team` | `Team`, `TeamResult`, `TeamStatus` |
| `sdk.events` | `EventEmitter` |
| `sdk.hooks` | `Hooks`, `TaskLoopEventHandler` |
| `sdk.memory` | `Memory` |
| `sdk.knowledge` | `KnowledgeBase`, `AgenticRetriever`, `GraphKnowledgeBase` |
| `sdk.multimodal` | `MultimodalAgent`, `Attachment` |
| `sdk.evaluation` | `Evaluator`, `ExactMatchMetric`, `LLMAsJudgeMetric`, `HITTEvaluator`, `EvalResult` |
| `sdk.tracing` | `OtelTracer`, `OtelTracerConfig` |
| `sdk.workspace` | `Workspace`, `WorkspaceConfig` |
| `sdk.rollout` | `MultiRollout`, `MultiRolloutConfig`, `RolloutResult` |
| `sdk.swarm` | `SwarmFlow`, `SwarmResult` |
| `sdk.permissions` | `PermissionEngine` |
| `sdk.context` | `ContextEngine` |
| `sdk.lsp` | `LSPIntegration` |
| `sdk.rl` | `OnlineRL`, `RLConfig` |
| `sdk.builder` | `AgentBuilder`, `PromptBuilder` |
| `sdk.mcp` | `MCPServer` |
| `sdk.a2a` | `RemoteAgent`, `A2AResult` |
| `sdk.config` | `ModelConfig`, `RemoteConfig`, `SdkConfig` |
| `sdk.errors` | `SdkError`, `ConnectionError`, `AuthError`, `SessionNotFoundError`, `ToolError`, `TimeoutError`, `ProtocolError` |
| `sdk.contrib` | `InMemoryCheckpointBackend`, `RedisCheckpointBackend` |

---

## TypeScript SDK — features

```typescript
import { JiuwenSwarmClient, SessionManager } from "@jiuwenswarm/sdk";

const client = new JiuwenSwarmClient({
  url: "wss://prod.example.com:19000/v1/ws",
  authToken: process.env.JIUWENSWARM_TOKEN,
  onToken: (text) => process.stdout.write(text),
  onDone: (sessionId) => console.log("\nDone:", sessionId),
  reconnect: { maxAttempts: 5, initialDelayMs: 1000, factor: 2 },
});

const sessions = new SessionManager(client);
await client.connect();
await sessions.create("My session");
client.send("Hello!", { sessionId: sessions.active?.session_id });
```

**Events emitted by `JiuwenSwarmClient`:**

| Event | Arguments | When |
|-------|-----------|------|
| `"connected"` | `[]` | WebSocket opened |
| `"disconnected"` | `[reason]` | Connection closed |
| `"token"` | `[text, sessionId]` | Streamed token received |
| `"done"` | `[sessionId]` | Agent run complete |
| `"error"` | `[message]` | Error received |
| `"reconnecting"` | `[attempt, delayMs]` | Reconnect attempt starting |

**Reconnect backoff:** 1 s → 2 s → 5 s → 10 s → 30 s (capped).

---

## Gateway REST API

Start the gateway:

```bash
python -m openjiuwen.gateway \
  --auth-token "$(cat /run/secrets/gateway_token)" \
  --port-rest 19001 \
  --port-ws 19000
```

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/health` | Health check + protocol version |
| GET | `/v1/sessions` | List sessions |
| POST | `/v1/sessions` | Create session |
| GET | `/v1/sessions/{id}` | Session detail + messages |
| DELETE | `/v1/sessions/{id}` | Delete session |
| POST | `/v1/sessions/{id}/chat` | Blocking chat |
| POST | `/v1/sessions/{id}/chat/stream` | SSE streaming chat |
| GET | `/v1/agents` | List agents |
| GET | `/v1/agents/{id}` | Agent detail |
| POST | `/v1/agents/{id}/run` | Blocking agent run |
| POST | `/v1/agents/{id}/stream` | SSE agent stream |
| GET | `/v1/tools` | List tools |
| POST | `/v1/knowledge` | Create knowledge base |
| POST | `/v1/knowledge/{name}/documents` | Add documents |
| POST | `/v1/knowledge/{name}/query` | Query knowledge base |
| POST | `/v1/eval/batch` | Batch evaluation |
| POST | `/v1/agents/{id}/checkpoint` | Save checkpoint |
| GET | `/v1/checkpoints` | List checkpoints |
| POST | `/v1/checkpoints/{id}/restore` | Restore checkpoint |

OpenAPI spec and Swagger UI: `http://localhost:19001/docs`

WebSocket endpoint: `ws://localhost:19000/v1/ws` (protocol version `"1"`)

---

## Environment variables

### Python SDK

| Variable | Default | Description |
|----------|---------|-------------|
| `JIUWENSWARM_API_KEY` | — | Primary LLM API key |
| `OPENAI_API_KEY` | — | OpenAI key (fallback) |
| `ANTHROPIC_API_KEY` | — | Anthropic key |
| `JIUWENSWARM_PROVIDER` | `openai` | LLM provider |
| `JIUWENSWARM_MODEL` | `gpt-4o` | Model name |
| `JIUWENSWARM_URL` | `ws://localhost:19000` | Remote server URL |
| `JIUWENSWARM_TOKEN` | — | Remote auth bearer token |

### Gateway

| Variable | Default | Description |
|----------|---------|-------------|
| `JIUWENSWARM_GATEWAY_TOKEN` | — | Bearer token (unset = auth disabled) |
| `JIUWENSWARM_GATEWAY_HOST` | `0.0.0.0` | Bind address |
| `JIUWENSWARM_GATEWAY_PORT_REST` | `19001` | REST port |
| `JIUWENSWARM_GATEWAY_PORT_WS` | `19000` | WebSocket port |

---

## Examples

### Python (`examples/python/`)

| File | Shows |
|------|-------|
| `01_quick_start.py` | 10-line in-process and remote quick starts |
| `02_streaming.py` | Token streaming, event callbacks |
| `03_session_management.py` | Session CRUD, history |
| `04_custom_tools.py` | `@tool` decorator — sync and async |
| `05_workflow_dag.py` | DAG with branch and stream |
| `05b_workflow_basic.py` | Simple two-node linear workflow |
| `06_multimodal.py` | Image attachments with `MultimodalAgent` |
| `07_memory.py` | In-process persistent memory |
| `08_multi_agent_team.py` | Three-agent team with spawn and status |
| `09_knowledge_retrieval.py` | `KnowledgeBase`, `AgenticRetriever` |
| `10_evaluation.py` | `Evaluator`, `ExactMatchMetric`, `LLMAsJudgeMetric` |
| `11_otel_tracing.py` | OpenTelemetry span instrumentation |
| `12_workspace_operations.py` | `Workspace` — read, write, shell commands |
| `13_checkpoint_backends.py` | In-memory and Redis checkpoint backends |
| `14_agentic_retriever.py` | Multi-hop `AgenticRetriever` |
| `15_multi_rollout.py` | Parallel rollouts with `best_of` / `majority_vote` |
| `16_hooks_full.py` | `Hooks` + `TaskLoopEventHandler` full lifecycle |
| `16b_hooks_simple.py` | Simple `Hooks` quick-start |
| `17_a2a_full.py` | Full bidirectional A2A agent pair |
| `17b_a2a_client_only.py` | Client-only A2A call |
| `18_swarm_flow.py` | `SwarmFlow` with strategy selection |
| `19_permission_engine.py` | `PermissionEngine` tool-level access control |
| `20_graph_knowledge.py` | `GraphKnowledgeBase` entity + link traversal |
| `21_context_engine.py` | `ContextEngine` compression and injection |
| `22_hitt_evaluator.py` | `HITTEvaluator` human-in-the-loop scoring |
| `23_lsp_integration.py` | `LSPIntegration` — code completion + diagnostics |
| `24_online_rl.py` | `OnlineRL` PPO/DPO/GRPO training step |
| `25_agent_builder.py` | `AgentBuilder` fluent construction |
| `26_prompt_builder.py` | `PromptBuilder` — system, user, few-shot |
| `27_sub_workflow.py` | Nested `SubWorkflowNode` composition |
| `28_multi_session_streaming.py` | Multi-session fan-out streaming |
| `29_mcp_server.py` | `MCPServer` — expose team as MCP endpoints |

### TypeScript (`examples/typescript/`)

| File | Shows |
|------|-------|
| `01_connect_and_chat.ts` | Connect, send, stream tokens |
| `02_session_management.ts` | `SessionManager` CRUD |
| `03_streaming_events.ts` | All client events wired |
| `04_reconnect_config.ts` | Custom exponential backoff |
| `05_tool_call_custom.ts` | Client-side tool call handling |
| `06_tool_call_interception.ts` | `onToolCall` geolocation example |

### REST / cURL (`examples/rest/`)

| File | Shows |
|------|-------|
| `01_health_check.sh` | `GET /v1/health` |
| `02_session_crud.sh` | Create, get, list, delete sessions |
| `03_chat_blocking.sh` | Blocking `POST /v1/sessions/{id}/chat` |
| `04_chat_streaming.sh` | SSE `POST /v1/sessions/{id}/chat/stream` |
| `05_list_agents.sh` | `GET /v1/agents` |
| `06_knowledge_base.sh` | Create KB, add docs, query |
| `07_evaluation.sh` | `POST /v1/eval/batch` |
| `08_custom_auth.sh` | Bearer token in all requests |
| `09_checkpoint_restore.sh` | Save and restore a checkpoint |

---

## Documentation

| Document | Content |
|----------|---------|
| [`docs/overview.md`](docs/overview.md) | Feature tour with code examples |
| [`docs/architecture.md`](docs/architecture.md) | System design, bridge pattern, sequence diagrams |
| [`docs/api-reference.md`](docs/api-reference.md) | Every class, method, and parameter |
| [`docs/configuration.md`](docs/configuration.md) | All config objects and environment variables |
| [`docs/contributing.md`](docs/contributing.md) | How to add features, run tests, submit PRs |
| [`docs/roadmap.md`](docs/roadmap.md) | Remaining implementation tasks toward v1.0.0 |
| [`CHANGELOG.md`](CHANGELOG.md) | Version history |

TypeScript API reference (TypeDoc): `npm run docs` in `packages/sdk/`.

---

## Development setup

### Python

```bash
uv sync
make install
make test          # all unit tests (no keys needed — runtime is fully mocked)
make check         # lint staged files
make type-check    # pyright on sdk/ and gateway/
make fix           # black + isort + ruff --fix
```

### TypeScript

```bash
cd packages/sdk
npm install
npm test           # vitest
npm run build      # tsup → dist/
npm run docs       # TypeDoc → packages/sdk/docs/
```

### Running examples against a local server

```bash
# Start the gateway
python -m openjiuwen.gateway

# Python quick-start
OPENAI_API_KEY=sk-… python examples/python/01_quick_start.py

# TypeScript (requires ts-node or tsx)
cd packages/sdk && npx tsx ../../examples/typescript/01_connect_and_chat.ts

# REST
bash examples/rest/01_health_check.sh
```
