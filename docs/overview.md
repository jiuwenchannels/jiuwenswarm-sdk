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
from openjiuwen.sdk import PermissionEngine, PermissionRule, PermissionLevel

engine = PermissionEngine(rules=[
    PermissionRule(tool="shell", level=PermissionLevel.ASK),
    PermissionRule(tool="read_file", level=PermissionLevel.ALLOW),
    PermissionRule(tool="delete_file", level=PermissionLevel.DENY),
])
agent = await Agent.create("coder", model=cfg, permission_engine=engine)
```

### LSP integration

```python
from openjiuwen.sdk import LSPIntegration

agent = await Agent.create("coder", model=cfg)
lsp = LSPIntegration.attach(
    agent,
    server_cmd=["pyright-langserver", "--stdio"],
    root_uri="file:///path/to/project",
)

diagnostics = await lsp.diagnose("src/utils.py")
completions = await lsp.complete("src/utils.py", line=10, character=4)
await lsp.shutdown()
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
from openjiuwen.sdk import ContextEngine, ContextEngineConfig

engine = ContextEngine(ContextEngineConfig(
    max_messages=100,
    token_limit=16_000,
    compression_ratio=0.5,
))
agent = await Agent.create("coder", model=cfg, context_engine=engine)

# After agent.run():
stats = engine.last_stats   # ContextStats(input_tokens=..., compressions_applied=...)
```

### Online RL and trajectory collection

```python
from openjiuwen.sdk import OnlineRL, OfflineRL, RLConfig

def code_quality_reward(text: str) -> float:
    return 1.0 if "tests passed" in text else 0.1

agent = await Agent.create("rl-agent", model=cfg)

# Online: weight updates happen every rollouts_per_step steps
rl = OnlineRL(agent, RLConfig(algorithm="ppo", reward_fn=code_quality_reward, rollouts_per_step=8))
result = await rl.step("Write and test a binary search function.")
trajectories = rl.get_trajectories()

# Offline: collect trajectories, export for batch training
rl_off = OfflineRL(agent, RLConfig(online=False, reward_fn=code_quality_reward))
await rl_off.step("Write a sorting algorithm.")
rl_off.export_trajectories("trajectories.jsonl")
```

### MCP server exposure

```python
# SDK-embedded mode (recommended)
from openjiuwen.sdk import MCPServer

server = MCPServer(agents=[researcher, writer])
await server.start(host="localhost", port=9000)
# ... later:
await server.stop()

# Or as an async context manager:
async with MCPServer(agents=[researcher]) as server:
    ...   # server is running

# Subprocess mode — MCP stdio JSON-RPC (for Claude Desktop, etc.)
import subprocess, os
proc = subprocess.Popen(
    ["python", "-m", "openjiuwen.agent_teams.mcp"],
    stdin=subprocess.PIPE, stdout=subprocess.PIPE,
    env={**os.environ, "OPENJIUWEN_TEAM_JOIN": "team://my-team@localhost:9000"},
)
```

### Agent builder

```python
from openjiuwen.sdk import LlmAgentBuilder, AgentBuilder, PromptBuilder, ModelConfig

# Fluent LLM-agent builder
built = (
    LlmAgentBuilder()
    .name("assistant")
    .system_prompt("You are a helpful assistant.")
    .model("claude-3-5-sonnet-20241022")
    .temperature(0.7)
    .tool("web_search")
    .build()
)
await built.init()                        # initialises the underlying Agent
result = await built.run("Hello!")

# Generic builder (supports memory, workspace, knowledge bases)
built2 = (
    AgentBuilder("my-agent")
    .with_model(ModelConfig(provider="anthropic", model="claude-3-5-sonnet-20241022"))
    .with_tools([fetch_url, word_count])
    .with_memory(MemoryScope.USER)
    .build()
)
```

### Prompt builder

```python
from openjiuwen.sdk import PromptBuilder

prompt = (
    PromptBuilder()
    .system("You are a concise assistant.")
    .few_shot([
        ("What is 2+2?", "4"),
        ("Capital of France?", "Paris"),
    ])
    .user("What is the speed of light?")
    .build()
)

# Or get structured messages list for direct API use:
messages = PromptBuilder().system("Be helpful.").user("Hello").build_messages()
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
│   ├── workflow.py               Workflow DAG, LLMNode, ToolNode, ConditionNode,
│   │                             SubWorkflowNode, LLMComponent, Start, End
│   ├── a2a.py                    RemoteAgent (A2A client)
│   ├── hooks.py                  Hooks lifecycle container
│   ├── events.py                 EventEmitter
│   ├── team.py                   Team, TeamSpec
│   ├── config.py                 ModelConfig, RemoteConfig, SdkConfig
│   ├── errors.py                 SdkError hierarchy
│   ├── memory.py                 MemoryScope, Memory, MemoryRecord, make_memory
│   ├── knowledge.py              KnowledgeBase, Document, Retriever,
│   │                             AgenticRetriever, GraphKnowledgeBase, RetrievalResult
│   ├── workspace.py              Workspace, WorkspaceConfig
│   ├── multimodal.py             MultimodalAgent, ImageInput, AudioInput,
│   │                             VisionModelConfig, AudioModelConfig, Attachment
│   ├── rollout.py                MultiRolloutExecutor, MultiRolloutConfig, RolloutResult
│   ├── eval.py                   EvalCase, EvalResult, Metric, ExactMatchMetric,
│   │                             LLMAsJudgeMetric, MetricEvaluator, HITTEvaluator
│   ├── evaluation.py             re-exports everything from eval.py
│   ├── tracing.py                OtelTracer, OtelTracerConfig, init_otel_tracer, get_tracer
│   ├── context.py                ContextEngine, ContextEngineConfig, ContextStats
│   ├── permissions.py            PermissionEngine, PermissionLevel, PermissionRule
│   ├── lsp.py                    LSPIntegration, LSPDiagnostic, LSPCompletionItem
│   ├── rl.py                     OnlineRL, OfflineRL, RLConfig, RLTrajectory
│   ├── builder.py                AgentBuilder, LlmAgentBuilder, WorkflowBuilder,
│   │                             PromptBuilder
│   ├── swarm.py                  SwarmFlow, SwarmResult (OOP interface)
│   ├── swarmflow.py              parallel, pipeline, phase, run_swarmflow (functional)
│   ├── mcp.py                    MCPServer façade
│   ├── contrib/
│   │   ├── memory_checkpoint.py  InMemoryCheckpointBackend
│   │   └── redis_checkpoint.py   RedisCheckpointBackend (optional; requires redis-py)
│   ├── extensions/
│   │   ├── __init__.py           register_store, get_store, register_checkpointer, get_checkpointer
│   │   ├── store.py              BaseSessionStore abstract class
│   │   └── checkpointer.py       BaseCheckpointer abstract class
│   └── _internal/
│       ├── runner_bridge.py      wraps openjiuwen.core Runner
│       ├── session_bridge.py     wraps SessionManager
│       ├── remote_bridge.py      WebSocket/REST client calls
│       ├── workflow_bridge.py    wraps workflow runtime
│       ├── memory_bridge.py      wraps memory store
│       ├── knowledge_bridge.py   wraps knowledge store
│       ├── swarm_bridge.py       wraps swarm execution
│       ├── mcp_bridge.py         wraps MCP server
│       ├── permission_bridge.py  wraps permission engine
│       └── sync_wrapper.py       run_sync helper
│
├── gateway/                      HTTP + WebSocket gateway (Phase 3)
│   ├── app.py                    build_gateway_app()
│   ├── auth.py                   Bearer token middleware
│   ├── rest/                     FastAPI route handlers
│   └── ws/                       WebSocket handler and dispatcher
│
└── agent_teams/
    └── mcp.py                    MCP stdio entrypoint (subprocess mode)

packages/
└── sdk/                          TypeScript SDK (@jiuwenswarm/sdk) (Phase 4)
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
