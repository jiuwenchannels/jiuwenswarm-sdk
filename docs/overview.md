# JiuwenSwarm SDK — Overview

## What This Project Is

`openjiuwen-sdk` is the Python SDK for the JiuwenSwarm agent runtime.
It provides a clean, versioned public API over the internal
`openjiuwen.core` and `openjiuwen.harness` packages, so application
developers can build and orchestrate AI agents without needing to know
anything about the runtime internals.

The SDK is distributed as a namespace package under `openjiuwen.sdk`.
Install it with:

```bash
pip install openjiuwen-sdk            # remote / A2A mode only
pip install openjiuwen-sdk[runtime]   # includes the in-process runtime
```

---

## What Is Built

### Agent execution

Two entry points for running an agent:

| Mode | Class method | Description |
|------|-------------|-------------|
| In-process | `Agent.create()` | The full JiuwenSwarm runtime runs inside your Python process. Configure the LLM with `ModelConfig`. No separate server needed. |
| Remote WebSocket | `Agent.connect()` | Connects to a running JiuwenSwarm server over the WebSocket envelope protocol. |

Both modes expose the same `Agent` interface:

```python
result = await agent.run("prompt")          # blocking, returns AgentResult
async for token in agent.stream("prompt"):  # token-by-token streaming
    print(token, end="", flush=True)

agent.on("tool_call", callback)             # event subscription
checkpoint_id = await agent.checkpoint()   # save state
agent2 = await Agent.restore(checkpoint_id) # reload state
result = agent.run_sync("prompt")           # sync wrapper for scripts
```

### Configuration

**`ModelConfig`** — frozen dataclass for in-process LLM configuration:
- `provider` (`"openai"` | `"anthropic"` | `"siliconflow"` | custom)
- `model`, `api_key`, `api_base`, `temperature`, `max_tokens`, `timeout`, `max_retries`
- `ModelConfig.from_env()` reads `JIUWENSWARM_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`

**`RemoteConfig`** — frozen dataclass for WebSocket remote connections:
- `url`, `auth_token`, `timeout`, `max_retries`
- `RemoteConfig.from_env()` reads `JIUWENSWARM_URL` and `JIUWENSWARM_TOKEN`

### Session management

```python
session = await Session.create("title", mode="default")
sessions = await Session.list()
session = await Session.get(session_id)
await session.delete()
messages = await session.history()   # list[Message]
```

Sessions persist across agent restarts. Pass `session_id=` to `agent.run()` to
continue an existing conversation.

### Custom tools

```python
@tool(name="fetch_url", description="Fetch the text of a URL.")
async def fetch_url(url: str) -> str:
    async with httpx.AsyncClient() as client:
        return (await client.get(url)).text

agent = await Agent.create("my-agent", model=cfg, tools=[fetch_url])
```

Supports: sync and async functions, all JSON-schema types inferred from
annotations, optional parameters via defaults, enum constraints via
`ToolParam`, direct invocation via `tool.ainvoke()` / `invoke_sync()`.

### Workflow (DAG orchestration)

```python
wf = (
    Workflow.create("pipeline", model=cfg)
    .add_node(LLMNode("Summarise: {text}", name="summarise"))
    .add_node(LLMNode("Translate to French: {text}", name="translate"))
    .connect("summarise", "translate")
)
result = await wf.run({"text": "..."})
async for event in wf.stream({"text": "..."}):
    print(event)
diagram = wf.draw()   # Mermaid string
```

Node types: `LLMNode`, `ToolNode`, `ConditionNode`. The compiled graph is
cached; it recompiles only on structural change.

### Multi-agent team

```python
team = await Team.create([researcher, writer, reviewer])
result = await team.spawn("Research and write a report on quantum computing.")
await team.send("Add a conclusion section.", to="writer")
```

Returns a `TeamResult` with the final output and per-agent contributions.

### A2A remote agent client

Call any JiuwenSwarm agent over the A2A protocol without knowing its
internal implementation:

```python
async with RemoteAgent("http://host:9000", "agent-id") as agent:
    result = await agent.run("prompt")           # returns A2AResult
    async for token in agent.stream("prompt"):   # streaming
        print(token, end="")
    await agent.cancel(task_id)
```

### Lifecycle hooks

```python
hooks = Hooks()

@hooks.token
async def on_token(text: str) -> None:
    print(text, end="", flush=True)

@hooks.tool_call
async def on_tool_call(name: str, args: dict) -> None:
    print(f"[tool] {name}({args})")

agent = await Agent.create("my-agent", model=cfg, hooks=hooks)
```

Six event slots: `on_token`, `on_tool_call`, `on_tool_result`, `on_done`,
`on_error`, `on_start`. Multiple callbacks per slot. Both decorator and
constructor form supported.

### EventEmitter

```python
emitter = EventEmitter()
emitter.on("token", callback)
emitter.emit("token", "text")          # schedules async callbacks on loop
await emitter.emit_async("token", "text")  # awaits all callbacks
emitter.off("token", callback)
emitter.off_all("token")
```

### Error hierarchy

```
SdkError
├── ConnectionError
├── AuthError
├── SessionNotFoundError
├── ToolError
├── TimeoutError
├── ProtocolError
├── WorkflowError
├── A2AError
├── ServerError          # carries .status_code
└── ConfigError
```

All errors importable from `openjiuwen.sdk`.

---

## Module layout

```
openjiuwen/sdk/
├── __init__.py              public re-exports
├── agent.py                 Agent façade
├── session.py               Session façade
├── tools.py                 @tool decorator, SdkTool, ToolParam
├── workflow.py              Workflow DAG façade
├── a2a.py                   RemoteAgent (A2A client)
├── hooks.py                 Hooks container
├── events.py                EventEmitter
├── team.py                  Team façade
├── config.py                ModelConfig, RemoteConfig, SdkConfig
├── errors.py                SdkError hierarchy
└── _internal/
    ├── runner_bridge.py     delegates to openjiuwen.core Runner
    ├── session_bridge.py    delegates to core SessionManager
    ├── team_bridge.py       delegates to core team runtime
    ├── workflow_bridge.py   delegates to core workflow runtime
    └── sync_wrapper.py      run_sync event-loop helper

tests/unit_tests/sdk/        fast, deterministic, no live runtime
tests/system_tests/sdk/      E2E against a live local server
examples/python/             runnable scripts §01–§29
examples/typescript/         TypeScript SDK examples §01–§06
examples/rest/               cURL/shell REST examples §01–§09
docs/                        API reference, architecture, contributing, roadmap
```

---

## Environment variables

| Variable | Used by | Description |
|----------|---------|-------------|
| `JIUWENSWARM_API_KEY` | `ModelConfig.from_env()` | Primary API key (any provider) |
| `OPENAI_API_KEY` | `ModelConfig.from_env()` | Fallback for OpenAI provider |
| `ANTHROPIC_API_KEY` | `ModelConfig.from_env()` | Fallback for Anthropic provider |
| `JIUWENSWARM_URL` | `RemoteConfig.from_env()` | WebSocket server URL (default: `ws://localhost:19000`) |
| `JIUWENSWARM_TOKEN` | `RemoteConfig.from_env()` | Bearer auth token for remote connection |
| `JIUWENSWARM_MODEL` | `SdkConfig.from_env()` | Default model name |
| `OPENJIUWEN_TEAM_JOIN` | MCP server (`§29`) | Team discovery URL, e.g. `team://my-team@localhost:9000` |

---

## Tests

156 unit tests, all passing:

| Suite | Tests | Coverage |
|-------|-------|---------|
| `test_config.py` | env loading, defaults, validation |
| `test_events.py` | register, fire, remove, multiple listeners |
| `test_agent.py` | run, stream, events, checkpoint, run_sync |
| `test_session.py` | CRUD, history, message ordering |
| `test_tools.py` | decoration, schema inference, invocation |
| `test_team.py` | create, spawn, send, status |
| `test_workflow.py` | node types, builder API, run, stream, draw |
| `test_a2a.py` | run, stream, cancel, context manager |
| `test_hooks.py` | constructor, decorators, wire, agent integration |

Run: `make test TESTFLAGS="tests/unit_tests/sdk/"`
