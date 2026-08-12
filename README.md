# JiuwenSwarm Python SDK

`openjiuwen-sdk` is the Python client library for JiuwenSwarm. It exposes the
JiuwenSwarm runtime — agents, sessions, tools, workflows, teams, and
agent-to-agent calls — through a concise async API that fits in 10 lines.

```python
import asyncio
from openjiuwen.sdk import Agent, ModelConfig

async def main():
    agent = await Agent.create("researcher", model=ModelConfig.from_env())
    result = await agent.run("Explain the CAP theorem in one paragraph.")
    print(result.text)

asyncio.run(main())
```

## What this package is

| Package | Language | Status |
|---------|----------|--------|
| **`openjiuwen-sdk`** (this repo) | Python 3.9+ | **Available** |
| `@jiuwenswarm/sdk` | TypeScript / JavaScript | Planned |
| HTTP REST + WebSocket gateway | Server (any language via curl) | Planned |

The TypeScript SDK and the HTTP gateway are separate projects. They share the
same protocol design and usage examples, but are not part of this repository.

## Installation

```bash
pip install openjiuwen-sdk          # SDK facade only (remote mode)
pip install openjiuwen-sdk[runtime] # + in-process runtime (Agent.create)
```

Remote mode (`Agent.connect`) needs only the base install.
In-process mode (`Agent.create`) additionally requires the `openjiuwen` runtime.

## Two execution modes

### In-process

The JiuwenSwarm runtime runs inside your Python process. Gives you full access
to `checkpoint`, `workspace`, `event_handler`, `hooks`, and custom backends.

```python
from openjiuwen.sdk import Agent, ModelConfig

agent = await Agent.create(
    "planner",
    model=ModelConfig(provider="openai", model="gpt-4o", api_key="sk-…"),
)
result = await agent.run("Plan a three-day trip to Kyoto.")
```

### Remote

The runtime runs in a separate JiuwenSwarm server process. Your code connects
over WebSocket and uses the same `run` / `stream` / `on` API.

```python
from openjiuwen.sdk import Agent

agent = await Agent.connect("ws://localhost:19000/v1/ws", auth_token="…")
result = await agent.run("Plan a three-day trip to Kyoto.")
```

## Core API surface

```
Agent.create()          build an in-process agent
Agent.connect()         connect to a remote server
Agent.create_sync()     synchronous variant of create()

agent.run(prompt)                   → AgentResult
agent.run_sync(prompt)              → AgentResult (no event loop needed)
agent.stream(prompt)                → AsyncIterator[str]
agent.checkpoint()                  → checkpoint_id
Agent.restore(checkpoint_id)        → Agent

agent.on(event, callback)
agent.off(event, callback)

Session.create(title)
Session.list()
Session.get(session_id)
session.history()
session.delete()

@tool                               register a function as an agent tool

Team.create(agents)                 assemble a multi-agent team
team.spawn(prompt)                  → TeamResult

Workflow.create(name)               build a DAG workflow
workflow.add_node(id, node)
workflow.connect(src, dst)
workflow.branch(src, cond, …)
workflow.run(inputs)                → WorkflowResult
workflow.stream(inputs)             → AsyncIterator[dict]
workflow.draw()                     → Mermaid diagram

RemoteAgent(url, agent_id)          A2A protocol client
remote_agent.run(prompt)            → A2AResult
remote_agent.stream(prompt)         → AsyncIterator[str]

Hooks()                             lifecycle callback container
hooks.token(fn)                     decorator: on streaming token
hooks.tool_call(fn)                 decorator: before tool executes
hooks.tool_result(fn)               decorator: after tool returns
hooks.done(fn)                      decorator: run complete
hooks.error(fn)                     decorator: on error
```

## Events emitted by Agent

| Event | Arguments | When |
|-------|-----------|------|
| `"token"` | `(token: str)` | Each streamed token |
| `"done"` | `()` | Run completed |
| `"error"` | `(msg: str)` | Run failed |
| `"tool_call"` | `(name: str, args: dict)` | Tool about to execute |
| `"tool_result"` | `(name: str, result: str)` | Tool returned |
| `"start"` | `(prompt: str)` | Run started |

## Environment variables

```
JIUWENSWARM_PROVIDER      openai | anthropic | siliconflow  (default: openai)
JIUWENSWARM_MODEL         model name                        (default: gpt-4o)
JIUWENSWARM_API_KEY       provider API key                  (fallback: OPENAI_API_KEY)
JIUWENSWARM_API_BASE      custom base URL
JIUWENSWARM_TEMPERATURE   float                             (default: 0.95)
JIUWENSWARM_MAX_TOKENS    int
JIUWENSWARM_URL           remote server URL                 (default: ws://localhost:19000/v1/ws)
JIUWENSWARM_TOKEN         remote auth bearer token
```

## Examples

Working examples are in the [`examples/`](examples/) directory:

| File | Shows |
|------|-------|
| `quick_start.py` | 10-line in-process and remote quick starts |
| `streaming.py` | Streaming tokens with event callbacks |
| `session_management.py` | Session CRUD and conversation history |
| `custom_tools.py` | `@tool` decorator, sync and async tools |
| `workflow_dag.py` | Multi-step DAG with branch and stream |
| `multi_agent_team.py` | Three-agent team with spawn and status |
| `hooks_lifecycle.py` | Lifecycle hooks on all agent events |
| `a2a_remote_agent.py` | Calling a remote agent via A2A protocol |

## Documentation

Full documentation lives in [`docs/`](docs/):

| Document | Content |
|----------|---------|
| [`docs/api-reference.md`](docs/api-reference.md) | Every class, method, and parameter |
| [`docs/roadmap.md`](docs/roadmap.md) | Planned features and upcoming phases |

## Development

```bash
uv sync
pip install -e ".[dev]"
pytest tests/
```

Tests use full mocking of the runtime layer — no LLM keys required.
