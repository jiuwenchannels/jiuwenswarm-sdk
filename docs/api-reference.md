# API Reference

All public symbols are importable from `openjiuwen.sdk`:

```python
from openjiuwen.sdk import Agent, ModelConfig, tool, Workflow, ...
```

Sub-module imports also work but are not part of the stable public API.

---

## Configuration

### `ModelConfig`

Frozen dataclass. Controls the LLM used in in-process mode.

```python
@dataclass(frozen=True)
class ModelConfig:
    provider: str = "openai"         # "openai" | "anthropic" | "siliconflow" | custom
    model: str = "gpt-4o"
    api_key: str | None = None       # falls back to OPENAI_API_KEY / ANTHROPIC_API_KEY
    api_base: str | None = None      # custom base URL
    temperature: float | None = None # default: 0.95
    max_tokens: int | None = None
    timeout: float = 60.0
    max_retries: int = 3
```

**Class method:**

```python
ModelConfig.from_env() -> ModelConfig
```

Reads `JIUWENSWARM_PROVIDER`, `JIUWENSWARM_MODEL`, `JIUWENSWARM_API_KEY`,
`JIUWENSWARM_API_BASE`, `JIUWENSWARM_TEMPERATURE`, `JIUWENSWARM_MAX_TOKENS`.
Falls back to `OPENAI_API_KEY` then `ANTHROPIC_API_KEY` when the generic key
is absent.

**Internal computed property:**

```python
config._normalised_provider  # "OpenAI" | "Anthropic" | "SiliconFlow" | …
```

---

### `RemoteConfig`

Frozen dataclass. Controls the connection to a remote JiuwenSwarm server.

```python
@dataclass(frozen=True)
class RemoteConfig:
    server_url: str = "ws://localhost:19000/v1/ws"
    auth_token: str | None = None
    timeout: float = 60.0
    max_retries: int = 3
```

**Class method:**

```python
RemoteConfig.from_env() -> RemoteConfig
```

Reads `JIUWENSWARM_URL` and `JIUWENSWARM_TOKEN`.

---

## Agent

### `Agent`

The primary entry point. Inherits from `EventEmitter`.

```python
class Agent(EventEmitter): ...
```

#### Constructors

```python
@classmethod
async def Agent.create(
    name: str,
    *,
    model: ModelConfig | None = None,      # defaults to ModelConfig.from_env()
    tools: list[SdkTool] | None = None,
    workspace: Any = None,
    memory_scope: Any = None,
    knowledge_bases: list[Any] | None = None,
    event_handler: Any = None,
    checkpoint_store: str | None = None,
    checkpoint_every: int | None = None,
    permission_engine: Any = None,
    context_engine: Any = None,
    rl_optimizer: Any = None,
    system_prompt: str | None = None,
    hooks: Hooks | None = None,
) -> Agent
```

Builds and eagerly initialises an in-process agent.
Requires the `openjiuwen` runtime (`pip install openjiuwen-sdk[runtime]`).

```python
@classmethod
async def Agent.connect(
    server_url: str,
    *,
    auth_token: str | None = None,
    config: RemoteConfig | None = None,
) -> Agent
```

Connects to a remote JiuwenSwarm server over WebSocket.

```python
@classmethod
def Agent.create_sync(
    name: str,
    *,
    model: ModelConfig | None = None,
    tools: list[SdkTool] | None = None,
    **kwargs,
) -> Agent
```

Blocking variant of `create()`. Works without a running event loop.

#### Execution

```python
async def agent.run(
    prompt: str,
    *,
    session_id: str | None = None,
) -> AgentResult
```

Runs the agent and returns the complete response. Creates a new session
automatically if `session_id` is omitted. Raises `SessionError` if the given
session ID does not exist.

```python
def agent.run_sync(
    prompt: str,
    *,
    session_id: str | None = None,
) -> AgentResult
```

Blocking variant of `run()`.

```python
async def agent.stream(
    prompt: str,
    *,
    session_id: str | None = None,
) -> AsyncIterator[str]
```

Yields text tokens as they stream from the model. Emits `"token"` events.
Emits `"done"` when complete.

#### Checkpoint

```python
async def agent.checkpoint() -> str
```

Saves agent state and returns a checkpoint ID (format: `ckpt_<hex12>`).
In-process mode only.

```python
@classmethod
async def Agent.restore(
    checkpoint_id: str,
    *,
    model: ModelConfig | None = None,
) -> Agent
```

Creates a new agent pre-loaded with the checkpoint state.

#### Lifecycle

```python
async def agent.close() -> None
```

Disconnects the remote WebSocket or releases in-process resources.

```python
# Context manager
async with await Agent.create("name") as agent:
    ...
```

#### Events

```python
agent.on(event: str, callback: Callable) -> None
agent.off(event: str, callback: Callable) -> None
agent.off_all(event: str | None = None) -> None
```

| Event | Signature | Description |
|-------|-----------|-------------|
| `"token"` | `(token: str)` | Streaming token arrived |
| `"done"` | `()` | Run completed |
| `"error"` | `(msg: str)` | Run failed |
| `"tool_call"` | `(name: str, args: dict)` | Tool about to execute |
| `"tool_result"` | `(name: str, result: str)` | Tool returned |
| `"start"` | `(prompt: str)` | Run started |

---

### `AgentResult`

```python
@dataclass
class AgentResult:
    text: str
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

---

## Session

### `Session`

```python
class Session:
    @classmethod
    def create(cls, title: str = "", mode: str = "default") -> Session

    @classmethod
    def list(cls) -> list[Session]

    @classmethod
    def get(cls, session_id: str) -> Session | None

    async def history(self) -> list[Message]

    def delete(self) -> None

    @property
    def session_id(self) -> str

    @property
    def title(self) -> str

    @property
    def mode(self) -> str
```

### `Message`

```python
@dataclass
class Message:
    role: str   # "user" | "assistant" | "system"
    text: str
```

---

## Tools

### `@tool` decorator

```python
@tool
def function_name(param: type) -> return_type:
    """Docstring becomes tool description."""
    ...

@tool(name="custom_name", description="Override description.", params=[...])
def function_name(...):
    ...
```

Wraps a function into an `SdkTool`. Supports both sync and async functions.
Parameter types are inferred from annotations:

| Python type | JSON schema type |
|-------------|-----------------|
| `str` | `"string"` |
| `int` | `"integer"` |
| `float` | `"number"` |
| `bool` | `"boolean"` |
| other | `"string"` |

Parameters with defaults are marked `required=False`.

### `SdkTool`

```python
@dataclass
class SdkTool:
    name: str
    description: str
    params: list[ToolParam]
    fn: Callable

    async def ainvoke(**kwargs) -> str
    def invoke_sync(**kwargs) -> str
    def to_tool_info() -> dict   # OpenAI function-call spec
```

### `ToolParam`

```python
@dataclass
class ToolParam:
    name: str
    type: str              # JSON schema type string
    description: str = ""
    required: bool = True
    enum: list | None = None
```

---

## Workflow

### `Workflow`

Fluent builder for DAG-based multi-step pipelines.

```python
@classmethod
def Workflow.create(
    name: str,
    *,
    model: ModelConfig | None = None,
    workflow_id: str | None = None,
) -> Workflow
```

```python
workflow.add_node(node_id: str, node: WorkflowNode) -> Workflow
workflow.connect(src: str, dst: str) -> Workflow
workflow.branch(
    src: str,
    condition: Callable[[], bool],
    *,
    true_target: str,
    false_target: str,
) -> Workflow

async def workflow.run(inputs: dict[str, Any]) -> WorkflowResult
async def workflow.stream(inputs: dict[str, Any]) -> AsyncIterator[dict]
def workflow.draw() -> str   # Mermaid diagram
```

All builder methods return `self` for chaining.
`add_node` invalidates the compiled graph so the next `run` recompiles.

### Node types

```python
@dataclass
class LLMNode(WorkflowNode):
    prompt_template: str
    name: str | None = None
    max_tokens: int | None = None

@dataclass
class ToolNode(WorkflowNode):
    tool: SdkTool
    name: str | None = None

@dataclass
class ConditionNode(WorkflowNode):
    condition: Callable[[], bool]
    true_target: str
    false_target: str
    name: str | None = None
```

### `WorkflowResult`

```python
@dataclass
class WorkflowResult:
    output: dict[str, Any]
    state: str              # "completed" | "input_required" | "error"
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

---

## Multi-agent Team

### `Team`

```python
@classmethod
async def Team.create(
    agents: list[Agent],
    *,
    model: ModelConfig | None = None,
    spec: Any = None,
    team_name: str = "sdk-team",
) -> Team

async def team.spawn(prompt: str) -> TeamResult
async def team.send(message: str, *, to: str | None = None) -> None
```

### `TeamResult`

```python
@dataclass
class TeamResult:
    final_output: str
    session_id: str | None = None
    member_outputs: dict[str, str] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
```

---

## A2A Remote Agent

### `RemoteAgent`

SDK client for a remote JiuwenSwarm agent reachable via the A2A protocol.

```python
RemoteAgent(
    url: str,
    agent_id: str,
    *,
    auth_token: str | None = None,
    timeout: float = 60.0,
)

async def remote_agent.run(
    prompt: str,
    *,
    task_id: str | None = None,
) -> A2AResult

async def remote_agent.stream(
    prompt: str,
    *,
    task_id: str | None = None,
) -> AsyncIterator[str]

async def remote_agent.cancel(task_id: str) -> bool
async def remote_agent.close() -> None

# Context manager
async with RemoteAgent(url, agent_id) as agent:
    ...
```

### `A2AResult`

```python
@dataclass
class A2AResult:
    text: str
    task_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

---

## Lifecycle Hooks

### `Hooks`

Convenience wrapper for registering agent lifecycle callbacks. Pass to
`Agent.create(hooks=...)`.

```python
Hooks(
    *,
    on_token: Callable[[str], Any] | list | None = None,
    on_tool_call: Callable[[str, dict], Any] | list | None = None,
    on_tool_result: Callable[[str, str], Any] | list | None = None,
    on_done: Callable[[], Any] | list | None = None,
    on_error: Callable[[Exception], Any] | list | None = None,
    on_start: Callable[[str], Any] | list | None = None,
)
```

**Decorator form:**

```python
hooks = Hooks()

@hooks.token
def on_tok(token: str) -> None: ...

@hooks.tool_call
def on_tool(name: str, args: dict) -> None: ...

@hooks.tool_result
def on_result(name: str, result: str) -> None: ...

@hooks.done
def on_done() -> None: ...

@hooks.error
def on_err(exc: Exception) -> None: ...

@hooks.start
def on_start(prompt: str) -> None: ...
```

**`hooks.wire(emitter)`** — bind all registered callbacks into an
`EventEmitter`. Called automatically by `Agent.create`.

Multiple callbacks per event are supported; all are called in registration order.

---

## EventEmitter

Mixin used by `Agent`.

```python
class EventEmitter:
    def on(event: str, callback: Callable) -> None
    def off(event: str, callback: Callable) -> None
    def off_all(event: str | None = None) -> None
    def emit(event: str, *args: Any) -> None
    async def emit_async(event: str, *args: Any) -> None
```

`emit` calls sync callbacks immediately and schedules async callbacks on the
running event loop. `emit_async` awaits all callbacks (both sync and async).

---

## Error hierarchy

```
SdkError
├── RuntimeNotAvailableError   openjiuwen runtime not installed
├── ConnectionError            WebSocket or A2A connection failed
├── AuthError                  Invalid or missing auth token
├── SessionError               Session not found or invalid
├── AgentError                 Agent invocation failed
├── ToolError                  Tool execution raised an exception
├── CheckpointError            Checkpoint save/restore failed
├── TeamError                  Team spawn or coordination failed
├── StreamError                Streaming broke mid-response
├── TimeoutError               Request exceeded timeout
└── ServerError(status_code, message)   HTTP 4xx/5xx from gateway
```

All errors inherit from `SdkError` which inherits from `RuntimeError`.

---

## Module layout

```
openjiuwen/sdk/
├── __init__.py          re-exports all public symbols
├── agent.py             Agent, AgentResult
├── config.py            ModelConfig, RemoteConfig
├── errors.py            SdkError hierarchy
├── events.py            EventEmitter
├── hooks.py             Hooks
├── session.py           Session, Message
├── team.py              Team, TeamResult
├── tools.py             @tool, SdkTool, ToolParam
├── workflow.py          Workflow, WorkflowResult, node types
├── a2a.py               RemoteAgent, A2AResult
└── _internal/
    ├── runner_bridge.py     in-process → DeepAgent
    ├── session_bridge.py    in-memory session registry
    ├── remote_bridge.py     WebSocket gateway client
    ├── workflow_bridge.py   workflow → runtime Workflow
    └── sync_wrapper.py      run_sync helper
```
