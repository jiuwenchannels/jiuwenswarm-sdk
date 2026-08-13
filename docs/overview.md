# JiuwenSwarm SDK — Overview

## What This Project Is

JiuwenSwarm is a multi-agent AI runtime. The SDK provides three ways to
reach it from application code:

| Access mode | Package | When to use |
|-------------|---------|-------------|
| **Python in-process** | `pip install openjiuwen-sdk[runtime]` | The runtime runs inside your Python process. Zero network. Ideal for scripts, notebooks, CLI tools. |
| **Python remote** | `pip install openjiuwen-sdk` | Connect to a running JiuwenSwarm server via WebSocket or REST. Same API as in-process. |
| **TypeScript / JavaScript** | `npm install @jiuwenswarm/sdk` | Browser, Node.js, React Native. Connects to the server via WebSocket. |
| **REST / cURL** | No package | Any language. HTTP client or `curl` against the gateway. |

All four modes share the same server runtime (`openjiuwen.core` +
`openjiuwen.harness`) and the same session, agent, and tool semantics.

---

## Installation

```bash
# Python — in-process mode (runtime included)
pip install openjiuwen-sdk[runtime]

# Python — remote / A2A mode only
pip install openjiuwen-sdk

# TypeScript
npm install @jiuwenswarm/sdk

# Start the HTTP + WebSocket gateway (for remote/TS/REST access)
python -m openjiuwen.gateway --host 0.0.0.0 --port-rest 19001 --port-ws 19000
```

---

## Python SDK

### Agent execution

Two constructors, one interface:

```python
from openjiuwen.sdk import Agent, ModelConfig, RemoteConfig

# In-process — runtime runs in your process
agent = await Agent.create("my-agent", model=ModelConfig(provider="openai", model="gpt-4o"))

# Remote — connects to a running server
agent = await Agent.connect("ws://localhost:19000/v1/ws", auth_token="tok")

# Same API for both:
result = await agent.run("Explain the GIL.")
async for token in agent.stream("Write a sonnet."):
    print(token, end="", flush=True)
```

**In-process `Agent.create()` parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `name` | `str` | Agent identifier |
| `model` | `ModelConfig` | LLM provider and model; defaults to `ModelConfig.from_env()` |
| `tools` | `list[SdkTool]` | Tools the agent may call |
| `workspace` | `Workspace \| None` | Bind agent to a directory |
| `memory_scope` | `MemoryScope \| None` | Enable long-term memory |
| `knowledge_bases` | `list[KnowledgeBase]` | RAG context sources |
| `event_handler` | `TaskLoopEventHandler \| None` | Full task-loop lifecycle hooks |
| `checkpoint_store` | `str \| None` | Named backend: `"sqlite"`, `"postgres"`, `"s3"`, … |
| `checkpoint_every` | `int \| None` | Auto-checkpoint every N turns |
| `hooks` | `Hooks \| None` | Lightweight lifecycle callbacks |
| `rl_optimizer` | `OnlineRLOptimizer \| None` | Online RL reward recording |
| `context_engine` | `ContextEngine \| None` | Context compression pipeline |
| `permission_engine` | `PermissionEngine \| None` | Tool permission policy |

**Shared Agent API:**

```python
result  = await agent.run(prompt, session_id=None)         # AgentResult
stream  = agent.stream(prompt, session_id=None)            # AsyncIterator[str]
ckpt_id = await agent.checkpoint()                         # str
agent2  = await Agent.restore(ckpt_id, model=cfg)          # Agent
result  = agent.run_sync(prompt)                           # sync wrapper
agent.on("token", cb)   # events: token, done, error, tool_call, tool_result
agent.off("token", cb)
```

### Session management

```python
from openjiuwen.sdk import Session

session  = await Session.create("title", mode="default")
sessions = await Session.list()
session  = await Session.get(session_id)
messages = await session.history()   # list[Message]
await session.delete()
```

### Custom tools

```python
from openjiuwen.sdk import tool, ToolParam

@tool(name="word_count", description="Count words in a text.")
def word_count(text: str) -> int:
    return len(text.split())

@tool(
    name="search",
    description="Search with a given mode.",
    params=[ToolParam("mode", description="Search mode", enum=["fast", "deep"])],
)
async def search(query: str, mode: str = "fast") -> str:
    ...

agent = await Agent.create("my-agent", model=cfg, tools=[word_count, search])
result = await word_count.ainvoke(text="hello world")  # direct call
```

### Workflow (DAG orchestration)

```python
from openjiuwen.sdk import Workflow, LLMNode, ToolNode, ConditionNode

wf = (
    Workflow.create("pipeline", model=cfg)
    .add_node(LLMNode("Summarise: {text}", name="summarise"))
    .add_node(LLMNode("Translate to French: {summary}", name="translate"))
    .connect("summarise", "translate")
)

result = await wf.run({"text": "..."})      # WorkflowResult
async for event in wf.stream({"text": "..."}):
    print(event)
diagram = wf.draw()                          # Mermaid string
```

Sub-workflow composition:

```python
from openjiuwen.sdk import SubWorkflowComponent

outer = (
    Workflow.create("outer")
    .add_node(SubWorkflowComponent(inner_wf, input_mapping={"x": "text"},
                                   output_mapping={"result": "summary"}))
    ...
)
```

### Multi-agent team

```python
from openjiuwen.sdk import Team

team   = await Team.create([researcher, writer, reviewer])
result = await team.spawn("Research and write a report on quantum computing.")
await team.send("Add a conclusion.", to="writer")
status = await team.status()
```

### A2A remote agent client

```python
from openjiuwen.sdk import RemoteAgent

async with RemoteAgent("http://host:9000", "agent-id") as remote:
    result = await remote.run("prompt")
    async for token in remote.stream("prompt"):
        print(token, end="")
    await remote.cancel(task_id)
```

### Lifecycle hooks

```python
from openjiuwen.sdk import Hooks

hooks = Hooks()

@hooks.token
async def on_token(text: str) -> None:
    print(text, end="", flush=True)

@hooks.tool_call
async def on_tool_call(name: str, args: dict) -> None:
    print(f"\n[tool] {name}({args})")

agent = await Agent.create("my-agent", model=cfg, hooks=hooks)
```

Six slots: `on_token`, `on_tool_call`, `on_tool_result`, `on_done`, `on_error`, `on_start`.

### Long-term memory

```python
from openjiuwen.sdk import MemoryScope

agent = await Agent.create("my-agent", model=cfg, memory_scope=MemoryScope.USER)
await agent.memory.add("User prefers concise answers.", metadata={"tag": "preference"})
results = await agent.memory.search("user preferences", top_k=3)
```

### Knowledge base and RAG

```python
from openjiuwen.sdk import KnowledgeBase, Retriever

kb = await KnowledgeBase.create("company-docs", embedding_model="text-embedding-3-small")
await kb.add_documents(["Refunds accepted within 30 days.", "Support: Mon–Fri 9–5 PST."])

retriever = Retriever(kb, strategy="hybrid")
results = await retriever.retrieve("What are support hours?", top_k=3)

agent = await Agent.create("support-bot", model=cfg, knowledge_bases=[kb])
```

Agentic retrieval (multi-round query rewriting):

```python
from openjiuwen.sdk import AgenticRetriever

agentic = AgenticRetriever(retriever, llm=cfg, max_rounds=3)
results = await agentic.retrieve("complex multi-part question")
```

Graph knowledge base:

```python
from openjiuwen.sdk import GraphKnowledgeBase

gkb = await GraphKnowledgeBase.create("knowledge-graph")
await gkb.add_documents(docs)          # extracts subject-predicate-object triples
results = await gkb.query("question", use_graph=True)
```

### SwarmFlow structured orchestration

```python
from openjiuwen.sdk import run_swarmflow, parallel, pipeline, phase

result = await run_swarmflow(
    phase([
        parallel([researcher_a, researcher_b], "gather data"),
        pipeline([writer, editor], "draft and refine"),
    ]),
    prompt="Produce a comprehensive market analysis.",
)
```

### Evaluation

```python
from openjiuwen.sdk import EvalCase, MetricEvaluator, ExactMatchMetric, LLMAsJudgeMetric

cases = [
    EvalCase(input="What is 2+2?", expected="4"),
    EvalCase(input="Capital of Japan?", expected="Tokyo"),
]
evaluator = MetricEvaluator(agent, metrics=[ExactMatchMetric(), LLMAsJudgeMetric()])
result = await evaluator.run(cases)
print(result.summary)   # {"exact_match": 0.5, "llm_judge": 0.975}
```

### Observability (OpenTelemetry)

```python
from openjiuwen.sdk import init_otel_tracer, OtelTracerConfig

init_otel_tracer(OtelTracerConfig(
    service_name="my-app",
    endpoint="http://localhost:4317",
))
# All subsequent agent runs, tool calls, and LLM calls emit OTLP spans.
```

### Workspace

```python
from openjiuwen.sdk import Workspace

ws = Workspace(root="/path/to/project", sandbox=True)
agent = await Agent.create("coder", model=cfg, workspace=ws)

diff = ws.diff()
modified = ws.modified_files
```

### Checkpoint and restore

```python
from openjiuwen.sdk import register_checkpointer
from openjiuwen.sdk.contrib.s3 import S3Checkpointer

register_checkpointer("s3", S3Checkpointer)

agent = await Agent.create(
    "coder",
    model=cfg,
    checkpoint_store="s3",
    checkpoint_every=5,
)

ckpt_id = await agent.checkpoint()
agent2  = await Agent.restore(ckpt_id, model=cfg)
```

### Multimodal inputs

```python
from openjiuwen.sdk import ImageInput, AudioInput

img   = ImageInput.from_file("/path/to/image.png")
img2  = ImageInput.from_url("https://example.com/photo.jpg")
audio = AudioInput.from_file("/path/to/audio.mp3")

result = await agent.run("Describe this image.", images=[img], audio=[audio])
```

### Multi-rollout

```python
from openjiuwen.sdk import MultiRolloutExecutor, MultiRolloutConfig

executor = MultiRolloutExecutor(agent, MultiRolloutConfig(n=8))
best = await executor.best_of("Write a function to sort a list.", evaluator=evaluator)
```

### Task loop event handler

```python
from openjiuwen.sdk import TaskLoopEventHandler, ToolGuard

class MyHandler(TaskLoopEventHandler):
    async def on_tool_call(self, name: str, args: dict):
        if name == "dangerous_op":
            return ToolResult(error="blocked")   # intercepts call

    async def on_done(self, result: str):
        print("Done:", result)

agent = await Agent.create(
    "my-agent", model=cfg,
    event_handler=MyHandler(),
)
```

### Security rails and permission engine

```python
from openjiuwen.sdk import PermissionEngine, PermissionsSection, CLIApprovalHost

engine = PermissionEngine([
    PermissionsSection(tool="shell", level="ask", host=CLIApprovalHost()),
    PermissionsSection(tool="read_file", level="allow"),
    PermissionsSection(tool="delete_file", level="deny"),
])
agent = await Agent.create("coder", model=cfg, permission_engine=engine)
```

### LSP integration

```python
from openjiuwen.sdk import lsp

await lsp.initialize_lsp(["pyright", "--stdio"])
lsp_tool = lsp.get_lsp_tool()
agent    = await Agent.create("coder", model=cfg, tools=[lsp_tool])

diagnostics = await lsp.get_pending_lsp_diagnostics()
await lsp.shutdown_lsp()
```

### Human-in-the-loop (HITT)

```python
from openjiuwen.sdk import Team, TeamMemberSpec, TeamAgentSpec, TeamRole

async def human_callback(message: str) -> str:
    return input(f"Agent says: {message}\nYour reply: ")

team = await Team.create([
    TeamAgentSpec("planner", agent=planner_agent),
    TeamMemberSpec("human", role=TeamRole.HUMAN_AGENT, callback=human_callback),
], enable_hitt=True)
```

### Context engine

```python
from openjiuwen.sdk import (
    ContextEngine, ToolResultBudgetProcessor,
    MessageSummaryOffloader, FullCompactProcessor,
)

engine = ContextEngine([
    ToolResultBudgetProcessor(max_chars=2000),
    MessageSummaryOffloader(threshold=20),
    FullCompactProcessor(),
])
agent = await Agent.create("coder", model=cfg, context_engine=engine)
stats = engine.last_stats   # {"before_tokens": 8200, "after_tokens": 3100}
```

### Online RL and trajectory collection

```python
from openjiuwen.sdk import OnlineRLOptimizer, RLConfig, RewardRegistry

registry = RewardRegistry()
registry.register("code_quality", lambda r: 1.0 if "tests passed" in r.outcome else 0.1)

optimizer = OnlineRLOptimizer(RLConfig(algorithm="ppo", lr=1e-4), registry)
agent     = await Agent.create("rl-agent", model=cfg, rl_optimizer=optimizer)

await agent.run("Write and test a binary search function.")
trajectories = optimizer.get_trajectories()
```

### MCP server exposure

```python
# Subprocess mode — speaks MCP stdio JSON-RPC
import subprocess, os
proc = subprocess.Popen(
    ["python", "-m", "openjiuwen.agent_teams.mcp"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    env={**os.environ, "OPENJIUWEN_TEAM_JOIN": "team://my-team@localhost:9000"},
)

# Embedded mode
from openjiuwen.agent_teams.mcp import build_server
from mcp.server.stdio import stdio_server
import asyncio

async def main():
    server = build_server()
    async with stdio_server() as (reader, writer):
        await server.run(reader, writer, server.create_initialization_options())

asyncio.run(main())
```

### Agent builder

```python
from openjiuwen.sdk import LlmAgentBuilder, WorkflowBuilder

agent = await (
    LlmAgentBuilder()
    .with_name("assistant")
    .with_model(ModelConfig(provider="anthropic", model="claude-3-5-sonnet-20241022"))
    .with_tools([fetch_url, word_count])
    .with_memory(MemoryScope.USER)
    .build()
)
```

### Prompt builder

```python
from openjiuwen.sdk import MetaTemplateBuilder, FeedbackPromptBuilder

candidates = await MetaTemplateBuilder(agent, n=5).generate("customer support bot")
refined    = await FeedbackPromptBuilder(agent).refine(prompt, bad_cases=[...])
```

### Custom backends

```python
from openjiuwen.sdk import register_store, register_checkpointer
from openjiuwen.sdk.contrib.postgres import PostgresSessionStore
from openjiuwen.sdk.contrib.s3 import S3Checkpointer

register_store("postgres", PostgresSessionStore)
register_checkpointer("s3", S3Checkpointer)

agent = await Agent.create(
    "my-agent", model=cfg,
    session_store="postgres",
    session_store_kwargs={"dsn": "postgresql://..."},
    checkpoint_store="s3",
    checkpoint_store_kwargs={"bucket": "my-checkpoints"},
)
```

---

## HTTP + WebSocket Gateway

Start the server:

```bash
python -m openjiuwen.gateway --host 0.0.0.0 --port-rest 19001 --port-ws 19000
```

Full REST route table:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/health` | Server status, version, protocol version |
| GET/POST | `/v1/sessions` | List or create sessions |
| GET/DELETE | `/v1/sessions/{id}` | Get or delete a session |
| POST | `/v1/sessions/{id}/chat` | Blocking chat |
| POST | `/v1/sessions/{id}/chat/stream` | SSE streaming chat |
| GET | `/v1/agents` | List registered agents |
| GET | `/v1/agents/{id}` | Get agent info |
| POST | `/v1/agents/{id}/run` | Run agent (blocking) |
| POST | `/v1/agents/{id}/stream` | Run agent (SSE) |
| GET | `/v1/tools` | List registered tools |
| POST | `/v1/knowledge` | Create knowledge base |
| POST | `/v1/knowledge/{name}/documents` | Add documents |
| POST | `/v1/knowledge/{name}/query` | Query knowledge base |
| POST | `/v1/eval/batch` | Run evaluation batch |
| POST | `/v1/agents/{id}/checkpoint` | Save checkpoint |
| GET | `/v1/checkpoints` | List checkpoints |
| POST | `/v1/checkpoints/{id}/restore` | Restore from checkpoint |

OpenAPI spec: `http://localhost:19001/docs`

WebSocket: `ws://localhost:19000/v1/ws`

---

## TypeScript SDK

```typescript
import { JiuwenSwarmClient } from "@jiuwenswarm/sdk";

const client = new JiuwenSwarmClient({
  url: "ws://localhost:19000/v1/ws",
  authToken: process.env.JIUWENSWARM_TOKEN,
  onToken: (text) => process.stdout.write(text),
  onDone: (sessionId) => console.log(`\n[done] ${sessionId}`),
  onError: (msg) => console.error(msg),
});

await client.connect();
const session = await client.sessions.create("My session");
client.sessions.setActive(session.id);
await client.send("Explain the event loop.");
client.disconnect();
```

Reconnects automatically with exponential back-off (1→2→5→10→30 s).
Intercept client-side tool calls with `onToolCall`.
Runs in browser, Node.js, and React Native.

---

## Module layout

```
openjiuwen/
├── sdk/                          Python SDK
│   ├── __init__.py               all public exports
│   ├── agent.py                  Agent façade
│   ├── session.py                Session façade
│   ├── tools.py                  @tool, SdkTool, ToolParam
│   ├── workflow.py               Workflow DAG, LLMNode, ToolNode, ConditionNode
│   ├── a2a.py                    RemoteAgent (A2A client)
│   ├── hooks.py                  Hooks lifecycle container
│   ├── events.py                 EventEmitter
│   ├── team.py                   Team, TeamSpec, SwarmFlow
│   ├── config.py                 ModelConfig, RemoteConfig, SdkConfig
│   ├── errors.py                 SdkError hierarchy
│   ├── memory.py                 MemoryScope, Memory
│   ├── knowledge.py              KnowledgeBase, Retriever, AgenticRetriever, GraphKnowledgeBase
│   ├── workspace.py              Workspace
│   ├── multimodal.py             ImageInput, AudioInput
│   ├── rollout.py                MultiRolloutExecutor, MultiRolloutConfig
│   ├── task_loop.py              TaskLoopEventHandler, ToolGuard, ToolResult
│   ├── eval.py                   EvalCase, MetricEvaluator, metrics
│   ├── observability.py          init_otel_tracer, OtelTracerConfig
│   ├── context_engine.py         ContextEngine and processors
│   ├── security.py               PermissionEngine, PermissionsSection
│   ├── lsp.py                    LSP integration
│   ├── rl.py                     OnlineRLOptimizer, OfflineRLOptimizer, RLConfig
│   ├── builder.py                LlmAgentBuilder, WorkflowBuilder
│   ├── prompt_builder.py         MetaTemplateBuilder, FeedbackPromptBuilder
│   ├── stores.py                 SessionStore, CheckpointerBackend protocols; register_*
│   ├── swarmflow.py              parallel, pipeline, phase, run_swarmflow
│   ├── contrib/
│   │   ├── postgres.py           PostgresSessionStore
│   │   └── s3.py                 S3Checkpointer
│   └── _internal/
│       ├── runner_bridge.py      wraps openjiuwen.core Runner
│       ├── session_bridge.py     wraps SessionManager
│       ├── remote_bridge.py      WebSocket/REST client calls
│       ├── team_bridge.py        wraps team runtime
│       ├── workflow_bridge.py    wraps workflow runtime
│       └── sync_wrapper.py       run_sync helper
│
├── gateway/                      HTTP + WebSocket gateway
│   ├── app.py                    build_gateway_app()
│   ├── auth.py                   Bearer token middleware
│   ├── rest/                     FastAPI route handlers
│   └── ws/                       WebSocket handler and dispatcher
│
└── agent_teams/
    └── mcp.py                    build_server(), MCP stdio entrypoint

packages/
└── sdk/                          TypeScript SDK (@jiuwenswarm/sdk)
    └── src/
        ├── client/               JiuwenSwarmClient, ReconnectScheduler
        ├── session/              SessionManager
        ├── protocol/             types, constants, validation
        └── events/               typed EventEmitter

examples/
├── python/                       §01–§29 Python examples
├── typescript/                   §01–§06 TypeScript examples
└── rest/                         §01–§09 REST / cURL examples

docs/
├── overview.md                   this file
├── api-reference.md              full API reference
├── architecture.md               design, bridges, sequences
├── configuration.md              all env vars and config classes
└── contributing.md               how to extend the SDK
```

---

## Environment variables

| Variable | Read by | Description |
|----------|---------|-------------|
| `JIUWENSWARM_API_KEY` | `ModelConfig.from_env()` | Primary LLM API key (any provider) |
| `OPENAI_API_KEY` | `ModelConfig.from_env()` | OpenAI key fallback |
| `ANTHROPIC_API_KEY` | `ModelConfig.from_env()` | Anthropic key fallback |
| `JIUWENSWARM_MODEL` | `ModelConfig.from_env()` | Default model name |
| `JIUWENSWARM_PROVIDER` | `ModelConfig.from_env()` | Default provider (`"openai"`, `"anthropic"`, …) |
| `JIUWENSWARM_URL` | `RemoteConfig.from_env()` | WebSocket server URL |
| `JIUWENSWARM_TOKEN` | `RemoteConfig.from_env()` | Bearer auth token |
| `JIUWENSWARM_GATEWAY_TOKEN` | gateway auth middleware | Server-side token for REST/WS auth |
| `OPENJIUWEN_TEAM_JOIN` | MCP server | Team discovery URL |
