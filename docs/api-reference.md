# API Reference

All public Python symbols are importable from `openjiuwen.sdk`:

```python
from openjiuwen.sdk import Agent, Session, tool, Workflow, Team, ...
```

Sub-module imports (`openjiuwen.sdk.agent`, etc.) are not part of the
stable public API.

---

## Configuration

### `ModelConfig`

```python
@dataclass(frozen=True)
class ModelConfig:
    provider: str = "openai"
    model: str = "gpt-4o"
    api_key: str | None = None
    api_base: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    timeout: float = 60.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> "ModelConfig": ...
```

### `RemoteConfig`

```python
@dataclass(frozen=True)
class RemoteConfig:
    server_url: str = "ws://localhost:19000/v1/ws"
    auth_token: str | None = None
    timeout: float = 60.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> "RemoteConfig": ...
```

### `SdkConfig`

```python
@dataclass(frozen=True)
class SdkConfig:
    model: ModelConfig = field(default_factory=ModelConfig)
    remote: RemoteConfig = field(default_factory=RemoteConfig)

    @classmethod
    def from_env(cls) -> "SdkConfig": ...
```

---

## AgentMode and ChannelId

Type-safe constants for the `mode` and `channel_id` parameters accepted by
`Agent.create()`, `Agent.connect()`, `Agent.run()`, `Agent.stream()`, and
`Agent.stream_events()`.

```python
from openjiuwen.sdk import AgentMode, ChannelId

agent = await Agent.create(
    "coder",
    model=cfg,
    mode=AgentMode.CODE,         # default mode for all requests
    channel_id=ChannelId.IDE,    # default channel for all requests
)

# Override per-call:
result = await agent.run("Write tests.", mode=AgentMode.CODE_TEAM)
```

### `AgentMode`

| Constant | Value | Description |
|---|---|---|
| `AgentMode.AGENT` | `"agent"` | General-purpose agent (default) |
| `AgentMode.CODE` | `"code"` | Code-focused mode — minimal prose |
| `AgentMode.TEAM` | `"team"` | Multi-agent team coordination |
| `AgentMode.CODE_TEAM` | `"code.team"` | Code + team (collaborative code generation) |
| `AgentMode.DEFAULT` | `"agent"` | Alias for `AGENT` |

```python
AgentMode.values() -> list[str]          # ["agent", "code", "team", "code.team"]
AgentMode.validate(value: str) -> str    # raises ValueError if unknown
```

### `ChannelId`

| Constant | Value | Description |
|---|---|---|
| `ChannelId.API` | `"api"` | Generic programmatic / REST channel (default) |
| `ChannelId.JUPYTER` | `"jupyter"` | JupyterLab extension channel |
| `ChannelId.IDE` | `"ide"` | JetBrains / VS Code extension channel |
| `ChannelId.BROWSER` | `"browser"` | Browser extension channel |
| `ChannelId.CLI` | `"cli"` | Command-line interface channel |

```python
ChannelId.values() -> list[str]   # ["api", "jupyter", "ide", "browser", "cli"]
```

> **Note:** `channel_id` only affects remote/gateway mode. In in-process mode it
> is forwarded in the request metadata but has no routing effect.

---

## Agent

```python
class Agent:
    @classmethod
    async def create(
        cls,
        name: str,
        *,
        model: ModelConfig | None = None,
        tools: list[SdkTool] | None = None,
        workspace: Workspace | None = None,
        memory_scope: MemoryScope | None = None,
        knowledge_bases: list[KnowledgeBase] | None = None,
        event_handler: TaskLoopEventHandler | None = None,
        checkpoint_store: str | None = None,
        checkpoint_every: int | None = None,
        hooks: Hooks | None = None,
        rl_optimizer: OnlineRLOptimizer | None = None,
        context_engine: ContextEngine | None = None,
        permission_engine: PermissionEngine | None = None,
        channel_id: str | None = None,   # default channel for all requests
        mode: str | None = None,         # default mode: "agent"|"code"|"team"|"code.team"
    ) -> "Agent": ...

    @classmethod
    async def connect(
        cls,
        server_url: str,
        *,
        auth_token: str | None = None,
        config: RemoteConfig | None = None,
        channel_id: str | None = None,
        mode: str | None = None,
    ) -> "Agent": ...

    async def run(
        self,
        prompt: str,
        *,
        session_id: str | None = None,
        mode: str | None = None,           # overrides default set at create()
        channel_id: str | None = None,     # overrides default set at create()
        context_prefix: str | None = None, # prepended to prompt with --- separator
        images: list[ImageInput] | None = None,
        audio: list[AudioInput] | None = None,
    ) -> "AgentResult": ...

    async def stream(
        self,
        prompt: str,
        *,
        session_id: str | None = None,
        mode: str | None = None,
        channel_id: str | None = None,
        context_prefix: str | None = None,
    ) -> AsyncIterator[str]: ...

    async def stream_events(
        self,
        prompt: str,
        *,
        session_id: str | None = None,
        mode: str | None = None,
        channel_id: str | None = None,
        context_prefix: str | None = None,
    ) -> AsyncIterator[StreamEvent]: ...

    def on(self, event: str, callback: Callable) -> None: ...
    def off(self, event: str, callback: Callable) -> None: ...

    async def checkpoint(self) -> str: ...

    @classmethod
    async def restore(
        cls,
        checkpoint_id: str,
        *,
        model: ModelConfig | None = None,
    ) -> "Agent": ...

    def run_sync(
        self,
        prompt: str,
        *,
        session_id: str | None = None,
        mode: str | None = None,
        channel_id: str | None = None,
        context_prefix: str | None = None,
    ) -> "AgentResult": ...

    @property
    def memory(self) -> "Memory": ...
```

**Events emitted on `agent.on(…)`:**

| Event | Arguments | When |
|---|---|---|
| `"token"` | `(text: str)` | Each streaming text token |
| `"reasoning"` | `(text: str)` | Each reasoning/thinking token |
| `"status"` | `(status: str)` | Processing status update |
| `"tool_call"` | `(name: str, args: dict)` | Tool invocation started |
| `"tool_result"` | `(name: str, result)` | Tool returned a result |
| `"done"` | `()` | Agent finished |
| `"error"` | `(msg: str)` | Agent encountered an error |

**`mode` values:** `"agent"` (default), `"code"` (code generation), `"team"` (multi-agent), `"code.team"` (code + team).
Use `AgentMode` constants instead of bare strings: `AgentMode.CODE`, `AgentMode.TEAM`, etc.

**`channel_id`:** Routes requests to a named channel on the jiuwenswarm server. Common values: `"api"`, `"jupyter"`, `"ide"`, `"browser"`, `"cli"`. Only affects remote/gateway mode; ignored in in-process mode.
Use `ChannelId` constants instead of bare strings: `ChannelId.API`, `ChannelId.JUPYTER`, etc.

**`context_prefix`:** Optional string prepended to `prompt` with a `\n\n---\n\n` separator before the request is dispatched. Mirrors the JupyterLab "inject context" pattern — use it to pass file contents, notebook cells, or IDE state to the agent without modifying the user-visible prompt.

### `AgentResult`

```python
@dataclass(frozen=True)
class AgentResult:
    text: str
    session_id: str
    metadata: dict
```

---

## Stream Events

Typed event objects yielded by `agent.stream_events()` and `team.stream()`.

```python
from openjiuwen.sdk import (
    StreamEvent,      # base class
    DeltaEvent,       # text token from the model
    ReasoningEvent,   # token from the model's thinking phase
    StatusEvent,      # processing status update
    ToolCallEvent,    # tool is about to be called
    ToolResultEvent,  # tool returned a result
    TeamEvent,        # multi-agent coordination event
    DoneEvent,        # stream completed
    ErrorEvent,       # stream ended with error
)
```

### Hierarchy

```python
@dataclass
class StreamEvent:
    type: str    # discriminator

@dataclass
class DeltaEvent(StreamEvent):
    type: Literal["delta"]
    delta: str

@dataclass
class ReasoningEvent(StreamEvent):
    type: Literal["reasoning"]
    delta: str       # reasoning/thinking token

@dataclass
class StatusEvent(StreamEvent):
    type: Literal["status"]
    status: str
    is_complete: bool

@dataclass
class ToolCallEvent(StreamEvent):
    type: Literal["tool_call"]
    tool_name: str
    arguments: dict[str, Any]
    call_id: str

@dataclass
class ToolResultEvent(StreamEvent):
    type: Literal["tool_result"]
    tool_name: str
    result: Any
    call_id: str
    is_error: bool

@dataclass
class TeamEvent(StreamEvent):
    type: str          # "team.agent_start" | "team.agent_done" | "team.handoff" | …
    agent_name: str
    payload: dict[str, Any]

@dataclass
class DoneEvent(StreamEvent):
    type: Literal["done"]
    text: str          # full assembled response

@dataclass
class ErrorEvent(StreamEvent):
    type: Literal["error"]
    message: str
```

### Usage pattern

```python
from openjiuwen.sdk import Agent, DeltaEvent, ReasoningEvent, ToolCallEvent, ToolResultEvent, DoneEvent

agent = await Agent.create("assistant", model=cfg, tools=[web_search])

async for event in agent.stream_events("What is the latest news on AI?"):
    match event.type:
        case "reasoning":
            print(f"[thinking] {event.delta}", end="")
        case "status":
            print(f"\n[{event.status}]")
        case "tool_call":
            print(f"\n→ {event.tool_name}({event.arguments})")
        case "tool_result":
            print(f"← {event.result}")
        case "delta":
            print(event.delta, end="", flush=True)
        case "done":
            print()
            break
```

### Low-level helpers

```python
# Convert a raw runtime chunk to a StreamEvent
parse_runtime_chunk(chunk: Any) -> StreamEvent

# Convert a gateway WebSocket envelope to a StreamEvent (or None for ack/housekeeping)
parse_gateway_envelope(env: dict) -> StreamEvent | None
```

---

## Session

```python
class Session:
    id: str
    title: str
    created_at: datetime
    mode: str

    @classmethod
    async def create(cls, title: str = "", mode: str = "default") -> "Session": ...

    @classmethod
    async def list(cls) -> list["Session"]: ...

    @classmethod
    async def get(cls, session_id: str) -> "Session": ...

    async def delete(self) -> None: ...
    async def history(self) -> list["Message"]: ...
```

### `Message`

```python
@dataclass(frozen=True)
class Message:
    role: str        # "user" | "assistant" | "tool"
    text: str
    timestamp: datetime
    metadata: dict
```

---

## Tools

### `@tool` decorator

```python
def tool(
    name: str,
    description: str,
    params: list[ToolParam] | None = None,
) -> Callable[[Callable], SdkTool]: ...
```

### `SdkTool`

```python
class SdkTool:
    name: str
    description: str

    def to_tool_info(self) -> dict: ...           # OpenAI function spec
    async def ainvoke(self, **kwargs) -> Any: ...
    def invoke_sync(self, **kwargs) -> Any: ...
```

### `ToolParam`

```python
@dataclass(frozen=True)
class ToolParam:
    name: str
    description: str = ""
    enum: list[str] | None = None
    required: bool = True
```

---

## Workflow

```python
class Workflow:
    @classmethod
    def create(cls, name: str, *, model: ModelConfig | None = None) -> "Workflow": ...

    def add_node(self, node: WorkflowNode) -> "Workflow": ...
    def connect(self, src: str, dst: str) -> "Workflow": ...
    def branch(self, src: str, condition: str, true_target: str, false_target: str) -> "Workflow": ...

    async def run(self, inputs: dict) -> "WorkflowResult": ...
    async def stream(self, inputs: dict) -> AsyncIterator[dict]: ...
    def draw(self) -> str: ...     # Mermaid diagram
```

### Node types

```python
@dataclass(frozen=True)
class LLMNode(WorkflowNode):
    prompt_template: str
    name: str = "llm"
    max_tokens: int | None = None

@dataclass(frozen=True)
class ToolNode(WorkflowNode):
    tool: SdkTool
    name: str = "tool"

@dataclass(frozen=True)
class ConditionNode(WorkflowNode):
    condition: str
    true_target: str
    false_target: str
    name: str = "condition"

@dataclass(frozen=True)
class SubWorkflowComponent(WorkflowNode):
    workflow: Workflow
    input_mapping: dict[str, str]
    output_mapping: dict[str, str]
    name: str = "sub-workflow"
```

### `WorkflowResult`

```python
@dataclass(frozen=True)
class WorkflowResult:
    output: dict
    state: str
    session_id: str
    metadata: dict
```

---

## Team

```python
class Team:
    @classmethod
    async def create(
        cls,
        agents: list[Agent],
        *,
        model: ModelConfig | None = None,
        spec: TeamAgentSpec | None = None,
        team_name: str | None = None,
    ) -> "Team": ...

    async def spawn(self, prompt: str) -> "TeamResult": ...

    async def stream(self, prompt: str) -> AsyncIterator[StreamEvent]: ...
    # Yields typed StreamEvent objects including TeamEvent for per-agent coordination.
    # Common TeamEvent.type values:
    #   "team.agent_start"  — an agent was assigned work
    #   "team.agent_done"   — an agent finished its subtask
    #   "team.handoff"      — leader routing work to a teammate
    # Always ends with a DoneEvent whose .text is the full assembled response.

    async def send(self, message: str, *, to: str | None = None) -> None: ...

@dataclass(frozen=True)
class TeamResult:
    final_output: str
    session_id: str
    member_outputs: dict[str, str]
```

#### `Team.stream()` example

```python
from openjiuwen.sdk import Team, Agent, DeltaEvent, TeamEvent, DoneEvent

researcher = await Agent.create("researcher", model=cfg)
writer     = await Agent.create("writer",     model=cfg)
team = await Team.create([researcher, writer], model=cfg)

async for event in team.stream("Research and write about quantum computing"):
    if isinstance(event, TeamEvent):
        print(f"[{event.type}] {event.agent_name}")
    elif isinstance(event, DeltaEvent):
        print(event.delta, end="", flush=True)
    elif isinstance(event, DoneEvent):
        print()
        break
```

### Human-in-the-loop

```python
class TeamRole(enum.Enum):
    AI_AGENT    = "ai_agent"
    HUMAN_AGENT = "human_agent"

@dataclass(frozen=True)
class TeamMemberSpec:
    name: str
    role: TeamRole
    callback: Callable[[str], Awaitable[str]]

@dataclass(frozen=True)
class TeamAgentSpec:
    name: str
    agent: Agent
```

---

## RemoteAgent (A2A)

```python
class RemoteAgent:
    def __init__(
        self,
        url: str,
        agent_id: str,
        *,
        auth_token: str | None = None,
        timeout: float = 60.0,
    ) -> None: ...

    async def run(self, prompt: str) -> "A2AResult": ...
    async def stream(self, prompt: str) -> AsyncIterator[str]: ...
    async def cancel(self, task_id: str) -> None: ...
    async def close(self) -> None: ...

    async def __aenter__(self) -> "RemoteAgent": ...
    async def __aexit__(self, *args) -> None: ...

@dataclass(frozen=True)
class A2AResult:
    text: str
    task_id: str
    metadata: dict
```

---

## Hooks

```python
@dataclass
class Hooks:
    on_token:       list[Callable] = field(default_factory=list)
    on_tool_call:   list[Callable] = field(default_factory=list)
    on_tool_result: list[Callable] = field(default_factory=list)
    on_done:        list[Callable] = field(default_factory=list)
    on_error:       list[Callable] = field(default_factory=list)
    on_start:       list[Callable] = field(default_factory=list)

    # Decorator form — each returns the function unchanged
    def token(self, fn: Callable) -> Callable: ...
    def tool_call(self, fn: Callable) -> Callable: ...
    def tool_result(self, fn: Callable) -> Callable: ...
    def done(self, fn: Callable) -> Callable: ...
    def error(self, fn: Callable) -> Callable: ...
    def start(self, fn: Callable) -> Callable: ...

    def wire(self, emitter: "EventEmitter") -> None: ...
```

---

## TaskLoopEventHandler

```python
class TaskLoopEventHandler:
    async def on_turn_start(self, turn: int) -> None: ...
    async def on_tool_call(self, name: str, args: dict) -> "ToolResult | None": ...
    async def on_tool_result(self, name: str, result: Any) -> None: ...
    async def on_llm_call(self, prompt: str) -> None: ...
    async def on_done(self, result: str) -> None: ...
    async def on_error(self, error: Exception) -> None: ...

@dataclass(frozen=True)
class ToolResult:
    result: Any = None
    error: str | None = None
```

Return a `ToolResult` from `on_tool_call` to intercept and block execution.

### `ToolGuard`

```python
class ToolGuard(TaskLoopEventHandler):
    def __init__(self, allowed_tools: list[str]) -> None: ...
    # Raises ToolError for any call not in allowed_tools
```

---

## Memory

```python
class MemoryScope(str, enum.Enum):
    USER    = "user"
    AGENT   = "agent"
    SESSION = "session"
    GLOBAL  = "global"

class Memory:
    async def add(self, text: str, *, metadata: dict | None = None) -> str: ...
    async def search(self, query: str, *, top_k: int = 5) -> list["MemoryRecord"]: ...
    async def clear(self) -> None: ...

@dataclass(frozen=True)
class MemoryRecord:
    text: str
    score: float
    metadata: dict
    id: str

def make_memory(scope: MemoryScope, user_id: str | None = None) -> Memory | None: ...
```

---

## Knowledge base and retrieval

```python
@dataclass
class Document:
    text: str
    metadata: dict = field(default_factory=dict)
    id: str | None = None

class KnowledgeBase:
    @classmethod
    async def create(
        cls,
        name: str,
        *,
        embedding_model: str = "text-embedding-3-small",
        vector_store: str = "chroma",
    ) -> "KnowledgeBase": ...

    async def add_documents(self, documents: list[Document]) -> None: ...
    async def query(self, query: str, *, top_k: int = 5) -> list["RetrievalResult"]: ...

class Retriever:
    def __init__(self, kb: KnowledgeBase, *, top_k: int = 5) -> None: ...
    async def retrieve(self, query: str, *, top_k: int | None = None) -> list["RetrievalResult"]: ...

class AgenticRetriever:
    def __init__(self, kb: KnowledgeBase, *, top_k: int = 5, max_hops: int = 3) -> None: ...
    async def retrieve(self, query: str, *, max_hops: int | None = None) -> list["RetrievalResult"]: ...

class GraphKnowledgeBase(KnowledgeBase):
    @classmethod
    async def create(
        cls,
        name: str,
        *,
        embedding_model: str = "text-embedding-3-small",
        vector_store: str = "chroma",
    ) -> "GraphKnowledgeBase": ...
    async def add_entity(self, entity_id: str, text: str, *, links: list[str] | None = None) -> None: ...
    async def retrieve(self, query: str, *, top_k: int = 5, use_graph: bool = True) -> list["RetrievalResult"]: ...

@dataclass(frozen=True)
class RetrievalResult:
    text: str
    score: float
    metadata: dict
```

---

## SwarmFlow

### OOP interface (`openjiuwen.sdk.swarm`)

```python
class SwarmFlow:
    @classmethod
    def create(
        cls,
        agents: list[Agent],
        strategy: str = "best_of",   # "best_of" | "majority_vote" | "first"
    ) -> "SwarmFlow": ...

    async def run(self, prompt: str, *, session_id: str | None = None) -> "SwarmResult": ...

@dataclass
class SwarmResult:
    output: str
    strategy: str
    candidates: list[str]
    metadata: dict
```

### Functional interface (`openjiuwen.sdk.swarmflow`)

```python
async def parallel(*tasks) -> list[str]: ...
async def pipeline(*tasks) -> str: ...
async def phase(name: str, *tasks) -> list[str]: ...
async def run_swarmflow(*, script, args, meta) -> "SwarmFlowResult": ...

@dataclass
class SwarmFlowResult:
    final_output: str
    phases: list[dict]
    metadata: dict
```

---

## Evaluation

```python
@dataclass
class EvalCase:
    input: str
    expected: str
    prediction: str = ""
    scores: dict[str, float] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

class Metric(abc.ABC):
    name: str
    async def score(self, case: EvalCase) -> float: ...

class ExactMatchMetric(Metric):   # name = "exact_match"
    ...

class LLMAsJudgeMetric(Metric):   # name = "llm_judge"
    def __init__(self, *, criteria: str = "quality", model: str = "gpt-4o") -> None: ...

class MetricEvaluator:
    def __init__(self, metrics: list[Metric]) -> None: ...
    async def batch_evaluate(self, cases: list[EvalCase]) -> list[EvalCase]: ...
    async def evaluate(self, case: EvalCase) -> EvalCase: ...
    def aggregate(self, cases: list[EvalCase]) -> "EvalResult": ...

Evaluator = MetricEvaluator   # alias

@dataclass
class EvalResult:
    cases: list[EvalCase]
    aggregate: dict[str, float]
    total_cases: int

class HITTEvaluator:
    def __init__(self, *, threshold: float = 0.7) -> None: ...
    def evaluate(self, result: EvalResult) -> "HITTResult": ...

@dataclass(frozen=True)
class HITTResult:
    review_fraction: float
    hitt_score: float
    review_count: int
```

---

## Observability

```python
@dataclass(frozen=True)
class OtelTracerConfig:
    endpoint: str = "http://localhost:4317"
    service_name: str = "jiuwenswarm"
    sample_rate: float = 1.0
    redact_llm_content: bool = False
    resource_attributes: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)

class OtelTracer:
    config: OtelTracerConfig
    def instrument(self, agent: Agent) -> None: ...
    def shutdown(self) -> None: ...

def init_otel_tracer(config: OtelTracerConfig | None = None) -> OtelTracer: ...
def get_tracer() -> OtelTracer | None: ...
```

---

## Workspace

```python
@dataclass(frozen=True)
class WorkspaceConfig:
    root: str = "."
    sandbox: bool = False
    sandbox_image: str = "python:3.11-slim"
    max_file_size: int = 10 * 1024 * 1024   # 10 MB
    allowed_extensions: tuple[str, ...] = ()

class Workspace:
    def __init__(
        self,
        root: str | Path = ".",
        *,
        sandbox: bool = False,
        sandbox_image: str = "python:3.11-slim",
        config: WorkspaceConfig | None = None,
    ) -> None: ...

    async def read(self, path: str | Path) -> str: ...
    async def write(self, path: str | Path, content: str) -> None: ...
    async def run_command(self, cmd: str | list[str], *, timeout: float = 60.0) -> str: ...
    async def diff(self) -> str: ...

    @property
    def root(self) -> Path: ...
    @property
    def modified_files(self) -> list[str]: ...
    @property
    def created_files(self) -> list[str]: ...
```

---

## Checkpoint backends

```python
class CheckpointerBackend:
    """Abstract base class. Subclass to create custom backends."""
    async def save(self, checkpoint_id: str, state: dict) -> None: ...
    async def load(self, checkpoint_id: str) -> dict: ...   # raises CheckpointError if missing
    async def list(self) -> list[str]: ...
    async def delete(self, checkpoint_id: str) -> None: ...

# Built-in (openjiuwen.sdk.contrib.memory_checkpoint)
class InMemoryCheckpointBackend(CheckpointerBackend): ...

# Optional (openjiuwen.sdk.contrib.redis_checkpoint)
class RedisCheckpointBackend(CheckpointerBackend):
    def __init__(self, url: str, *, key_prefix: str = "ckpt:", ttl: int | None = None) -> None: ...
```

Register custom backends with the extensions registry:

```python
from openjiuwen.sdk.extensions import register_checkpointer, get_checkpointer

register_checkpointer("memory", InMemoryCheckpointBackend())
backend = get_checkpointer("memory")
```

---

## Multimodal

```python
@dataclass(frozen=True)
class VisionModelConfig:
    model: str = "gpt-4o"
    max_tokens: int | None = None

@dataclass(frozen=True)
class AudioModelConfig:
    model: str = "whisper-1"
    language: str | None = None

@dataclass
class ImageInput:
    @classmethod
    def from_file(cls, path: str | Path) -> "ImageInput": ...
    @classmethod
    def from_url(cls, url: str) -> "ImageInput": ...
    def to_base64(self) -> str | None: ...

@dataclass
class AudioInput:
    @classmethod
    def from_file(cls, path: str | Path) -> "AudioInput": ...
    @classmethod
    def from_url(cls, url: str) -> "AudioInput": ...

@dataclass
class Attachment:
    @classmethod
    def from_file(cls, path: str | Path) -> "Attachment": ...
    def to_base64(self) -> str: ...

class MultimodalAgent:
    @classmethod
    async def create(
        cls,
        name: str,
        *,
        model: ModelConfig | None = None,
        vision_config: VisionModelConfig | None = None,
        audio_config: AudioModelConfig | None = None,
    ) -> "MultimodalAgent": ...

    async def run(
        self,
        prompt: str,
        *,
        attachments: list[Attachment] | None = None,
        images: list[ImageInput] | None = None,
        audio: list[AudioInput] | None = None,
        session_id: str | None = None,
    ) -> AgentResult: ...
```

---

## Multi-rollout

```python
@dataclass(frozen=True)
class MultiRolloutConfig:
    n: int = 3
    temperature: float | None = None
    concurrency: int = 3
    timeout: float | None = None

@dataclass
class RolloutResult:
    text: str
    session_id: str | None = None
    rollout_idx: int = 0
    metadata: dict = field(default_factory=dict)

class MultiRolloutExecutor:
    def __init__(self, agent: Agent, config: MultiRolloutConfig) -> None: ...
    async def run(self, prompt: str, *, session_id: str | None = None) -> list[RolloutResult]: ...
    async def best_of(self, results: list[RolloutResult], *, metric: Metric) -> RolloutResult: ...
    async def majority_vote(self, results: list[RolloutResult]) -> RolloutResult: ...
```

---

## Context engine

```python
@dataclass(frozen=True)
class ContextEngineConfig:
    max_messages: int = 200
    token_limit: int = 32_000
    compression_ratio: float = 0.5

@dataclass(frozen=True)
class ContextStats:
    input_tokens: int
    output_tokens: int
    compressions_applied: int

class ContextEngine:
    def __init__(self, config: ContextEngineConfig | None = None) -> None: ...
    def compress(self, messages: list) -> list: ...
    def inject(self, messages: list, text: str) -> list: ...
    def token_count(self, messages: list) -> int: ...
    last_stats: ContextStats | None
```

---

## Security rails

```python
class PermissionLevel(str, enum.Enum):
    ALLOW = "allow"
    ASK   = "ask"
    DENY  = "deny"

@dataclass(frozen=True)
class PermissionRule:
    tool: str = "*"
    agent: str = "*"
    level: PermissionLevel = PermissionLevel.ALLOW
    scope: str = "tool"    # "tool" | "agent" | "default"

class PermissionEngine:
    def __init__(
        self,
        rules: list[PermissionRule] | None = None,
        *,
        default_level: PermissionLevel = PermissionLevel.ALLOW,
    ) -> None: ...

    def check(self, agent_id: str, tool_name: str) -> bool: ...
    def allow(self, agent_id: str, tool_name: str) -> bool: ...  # alias for check
    def add_rule(self, rule: PermissionRule) -> None: ...

    @property
    def rules(self) -> list[PermissionRule]: ...
```

---

## LSP integration

```python
@dataclass(frozen=True)
class LSPPosition:
    line: int
    character: int

@dataclass(frozen=True)
class LSPRange:
    start: LSPPosition
    end: LSPPosition

@dataclass(frozen=True)
class LSPDiagnostic:
    message: str
    severity: str = "error"    # "error" | "warning" | "information" | "hint"
    range: LSPRange = ...
    source: str = ""
    code: str | None = None

@dataclass
class LSPCompletionItem:
    label: str
    kind: str = "text"
    detail: str = ""
    documentation: str = ""

class LSPIntegration:
    @classmethod
    def attach(
        cls,
        agent: Agent,
        server_cmd: list[str] | str,
        *,
        root_uri: str = "",
        language_id: str = "python",
    ) -> "LSPIntegration": ...

    async def complete(self, uri: str, *, line: int = 0, character: int = 0) -> list[LSPCompletionItem]: ...
    async def diagnose(self, uri: str) -> list[LSPDiagnostic]: ...
    async def shutdown(self) -> None: ...
```

---

## Online RL

```python
@dataclass(frozen=True)
class RLConfig:
    algorithm: str = "ppo"    # "ppo" | "dpo" | "grpo"
    reward_fn: Callable[[str], float] | None = None
    learning_rate: float = 1e-5
    rollouts_per_step: int = 4
    online: bool = True
    max_trajectory_len: int = 50

@dataclass
class RLTrajectory:
    prompt: str
    response: str
    reward: float = 0.0
    num_turns: int = 1
    metadata: dict = field(default_factory=dict)

@dataclass
class RLStepResult:
    text: str
    reward: float = 0.0
    session_id: str | None = None
    updated: bool = False

class OnlineRL:
    def __init__(self, agent: Agent, config: RLConfig) -> None: ...
    async def step(self, prompt: str, *, reward_fn: Callable[[str], float] | None = None) -> RLStepResult: ...
    def get_trajectories(self) -> list[RLTrajectory]: ...
    def clear_trajectories(self) -> None: ...

class OfflineRL:
    def __init__(self, agent: Agent, config: RLConfig) -> None: ...
    async def step(self, prompt: str, *, reward_fn: Callable[[str], float] | None = None) -> RLStepResult: ...
    def get_trajectories(self) -> list[RLTrajectory]: ...
    def export_trajectories(self, path: str) -> None: ...   # JSONL
```

---

## Builders

```python
class AgentBuilder:
    """Generic fluent builder."""
    def __init__(self, name: str = "agent") -> None: ...
    def with_model(self, model: ModelConfig) -> "AgentBuilder": ...
    def with_tools(self, tools: list[SdkTool]) -> "AgentBuilder": ...
    def with_hooks(self, hooks: Hooks) -> "AgentBuilder": ...
    def with_memory(self, scope: MemoryScope, *, user_id: str | None = None) -> "AgentBuilder": ...
    def with_system_prompt(self, prompt: str) -> "AgentBuilder": ...
    def with_workspace(self, workspace: Workspace) -> "AgentBuilder": ...
    def with_knowledge_bases(self, kbs: list[KnowledgeBase]) -> "AgentBuilder": ...
    def build(self) -> "_BuiltAgent": ...

class LlmAgentBuilder:
    """LLM-specific fluent builder."""
    def name(self, name: str) -> "LlmAgentBuilder": ...
    def system_prompt(self, prompt: str) -> "LlmAgentBuilder": ...
    def model(self, model_name: str) -> "LlmAgentBuilder": ...
    def temperature(self, temp: float) -> "LlmAgentBuilder": ...
    def max_turns(self, n: int) -> "LlmAgentBuilder": ...
    def tool(self, tool_name_or_obj: "str | SdkTool") -> "LlmAgentBuilder": ...
    def with_hooks(self, hooks: Hooks) -> "LlmAgentBuilder": ...
    def with_workspace(self, workspace: Workspace) -> "LlmAgentBuilder": ...
    def with_model_config(self, model_cfg: ModelConfig) -> "LlmAgentBuilder": ...
    def build(self) -> "_BuiltAgent": ...   # call await agent.init() before agent.run()

class WorkflowBuilder:
    def name(self, name: str) -> "WorkflowBuilder": ...
    def with_model_config(self, model_cfg: ModelConfig) -> "WorkflowBuilder": ...
    def add_component(self, component: WorkflowNode) -> "WorkflowBuilder": ...
    def add_edge(self, src, dst) -> "WorkflowBuilder": ...
    def build(self) -> "_BuiltWorkflowAgent": ...

class PromptBuilder:
    def system(self, text: str) -> "PromptBuilder": ...
    def user(self, text: str) -> "PromptBuilder": ...
    def assistant(self, text: str) -> "PromptBuilder": ...
    def few_shot(self, examples: list[tuple[str, str]]) -> "PromptBuilder": ...
    def build(self) -> str: ...
    def build_messages(self) -> list[dict[str, str]]: ...
```

---

## Prompt builders

`PromptBuilder` (implemented, part of `openjiuwen.sdk.builder`) covers structured prompt assembly.
See the **Builders** section above.

The following higher-order builders are planned for a future release:

```python
# Planned — not yet implemented
class MetaTemplateBuilder:
    def __init__(self, agent: Agent, n: int = 5) -> None: ...
    async def generate(self, task_description: str) -> list[str]: ...

class FeedbackPromptBuilder:
    def __init__(self, agent: Agent) -> None: ...
    async def refine(self, prompt: str, bad_cases: list[EvalCase]) -> str: ...
```

---

## EventEmitter

```python
class EventEmitter:
    def on(self, event: str, callback: Callable) -> None: ...
    def off(self, event: str, callback: Callable) -> None: ...
    def off_all(self, event: str) -> None: ...
    def emit(self, event: str, *args) -> None: ...              # schedules on loop
    async def emit_async(self, event: str, *args) -> None: ...  # awaits all
```

---

## Error hierarchy

```
SdkError
├── RuntimeNotAvailableError
├── ConnectionError
├── AuthError
├── SessionError
├── AgentError
├── ToolError
├── CheckpointError
├── TeamError
├── StreamError
├── TimeoutError
├── ServerError           carries .status_code and .message
└── WorkflowError         (raised by Workflow.run())
```

`A2AError` is raised by `RemoteAgent` operations and is a subclass of `SdkError`.

---

## TypeScript SDK

Package: `@jiuwenswarm/sdk` · `import { JiuwenSwarmClient } from "@jiuwenswarm/sdk"`

### `JiuwenSwarmClient`

```typescript
class JiuwenSwarmClient extends EventEmitter<ClientEvents> {
  constructor(config: ClientConfig)
  /** Open the WebSocket and complete the connect handshake. */
  connect(): Promise<void>
  /** Close the WebSocket and cancel any pending reconnect. */
  disconnect(): void
  /** The attached SessionManager (access via client.sessions). */
  readonly sessions: SessionManager
  /** Send a chat message; resolves when the server sends "done". */
  send(message: string): Promise<void>
  /** Low-level: send any outbound envelope. */
  sendEnvelope(envelope: OutboundEnvelope): void
}
```

### `ClientConfig`

```typescript
interface ClientConfig {
  /** WebSocket URL, e.g. "ws://localhost:19000/v1/ws" */
  url: string;
  /** Bearer token forwarded in the connect envelope. */
  authToken?: string;
  /** Called for each streaming token. */
  onToken?: (text: string) => void;
  /** Called when the agent finishes; receives the session ID. */
  onDone?: (sessionId?: string) => void;
  /** Called when the server sends an error envelope. */
  onError?: (message: string) => void;
  /**
   * Called for tool_call envelopes. Return the result string or throw
   * to send an error. Omit to auto-reject all tool calls.
   */
  onToolCall?: (call: ToolCallEnvelope) => Promise<string>;
  /** false to disable auto-reconnect; omit for defaults (1→2→5→10→30 s). */
  reconnect?: false | ReconnectConfig;
}

interface ReconnectConfig {
  maxAttempts?: number;    // default: Infinity
  initialDelayMs?: number; // default: 1 000
  maxDelayMs?: number;     // default: 30 000
  factor?: number;         // default: 2
}
```

### `SessionManager`

```typescript
class SessionManager {
  /** Fetch the session list from the server. */
  list(): Promise<SessionInfo[]>
  /** Create a new session and return it. */
  create(title: string, agentId?: string, mode?: AgentMode): Promise<SessionInfo>
  /** Mark a session as active; its ID is included in subsequent chat envelopes. */
  setActive(id: string): void
  /** Re-fetch the session list without changing the active session. */
  refresh(): Promise<void>
  /** The currently active session, or null. */
  get active(): SessionInfo | null
}
```

### `SessionInfo`

```typescript
interface SessionInfo {
  id: string;
  title: string;
  agent_id: string;
  mode: "default" | "focused" | "creative";
  created_at: string; // ISO 8601
}
```

### Events emitted by `JiuwenSwarmClient`

```typescript
type ClientEvents = {
  /** Fired when the WebSocket is open and the ack is received. */
  connected: [];
  /** Fired when the connection drops for any reason. */
  disconnected: [reason: string];
  /** Fired before each reconnect attempt. */
  reconnecting: [attempt: number, delayMs: number];
}
```

`token`, `done`, and `error` are delivered via the `onToken` / `onDone` / `onError`
callbacks in `ClientConfig`, not as events.

### `ToolCallEnvelope`

```typescript
interface ToolCallEnvelope {
  type: "tool_call";
  name: string;
  arguments: Record<string, unknown>;
  callId: string;
}
```

---

## REST API

Base URL: `http://localhost:19001`
Auth: `Authorization: Bearer <token>` (when auth is enabled on the server).

### Endpoints

| Method | Path | Request body | Response |
|--------|------|-------------|----------|
| GET | `/v1/health` | — | `{status, version, protocol_version}` |
| GET | `/v1/sessions` | — | `{sessions: SessionInfo[]}` |
| POST | `/v1/sessions` | `{title, agent_id, mode?}` | `{session: SessionInfo}` |
| GET | `/v1/sessions/{id}` | — | `{session: SessionInfo}` |
| DELETE | `/v1/sessions/{id}` | — | `{deleted: true, id}` |
| POST | `/v1/sessions/{id}/chat` | `{message, session_id?}` | `{response, session_id, metadata}` |
| POST | `/v1/sessions/{id}/chat/stream` | `{message, session_id?}` | SSE tokens |
| GET | `/v1/agents` | — | `{agents: AgentInfo[]}` |
| GET | `/v1/agents/{id}` | — | `{agent: AgentInfo}` |
| POST | `/v1/agents/{id}/run` | `{prompt, session_id?}` | `{response, session_id, metadata}` |
| POST | `/v1/agents/{id}/stream` | `{prompt, session_id?}` | SSE tokens |
| GET | `/v1/tools` | — | `{tools: ToolInfo[]}` |
| POST | `/v1/knowledge` | `{name, type?}` | `{knowledge_base: {name, type, document_count}}` |
| POST | `/v1/knowledge/{name}/documents` | `{documents: [{content, metadata?}]}` | `{added, knowledge_base}` |
| POST | `/v1/knowledge/{name}/query` | `{query, top_k?}` | `{results: [{content, score, metadata}]}` |
| POST | `/v1/eval/batch` | `{metric, cases: [{input, expected, prediction}]}` | `{results[], aggregate}` |
| POST | `/v1/agents/{id}/checkpoint` | — | `{checkpoint: {id, agent_id, created_at}}` |
| GET | `/v1/checkpoints` | — | `{checkpoints: CheckpointInfo[]}` |
| POST | `/v1/checkpoints/{id}/restore` | — | `{restored, agent_id, checkpoint_id}` |

Interactive docs: `http://localhost:19001/docs`

### SSE stream format

Streaming endpoints (`/chat/stream`, `/agents/{id}/stream`) emit
[Server-Sent Events](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events):

```
data: Hello

data:  world

data: [DONE]

```

Each `data:` line is one token. The stream ends with `data: [DONE]\n\n`.

### Error responses

All errors use the standard FastAPI shape:

```json
{"detail": "Human-readable error message"}
```

Common codes: `400` bad request, `401` unauthorized, `404` not found,
`409` conflict, `500` internal error.

---

## WebSocket Gateway

Endpoint: `ws://localhost:19000/v1/ws`

All messages are JSON **envelopes** — objects with a `"type"` discriminator.

### Inbound envelopes (client → server)

#### `connect`

Authenticate and identify the client. Required when `JIUWENSWARM_GATEWAY_TOKEN`
is set on the server (browser WS API cannot send `Authorization` headers).

```json
{"type": "connect", "client_type": "browser", "token": "<bearer-token>"}
```

#### `sessions`

Request the list of active sessions.

```json
{"type": "sessions"}
```

#### `create_session`

Create a new session and make it active for this connection.

```json
{
  "type": "create_session",
  "agent_id": "researcher",
  "title": "My session",
  "mode": "default"
}
```

#### `chat`

Send a message and receive a streamed reply. `session_id` is optional when a
session was already activated via `create_session`.

```json
{"type": "chat", "message": "Explain transformer attention.", "session_id": "sess_abc"}
```

### Outbound envelopes (server → client)

| `"type"` | When | Key fields |
|----------|------|-----------|
| `ack` | After `connect` or `chat` received | `protocol_version`, `client_type`, `session_id` |
| `sessions` | Reply to `sessions` request | `sessions: SessionInfo[]` |
| `session_created` | Reply to `create_session` | `session: SessionInfo` |
| `token` | During streaming | `text: string` |
| `done` | End of stream | `session_id` |
| `error` | Any error | `message: string` |

### WebSocket example (Python)

```python
import asyncio, json, websockets

async def main():
    async with websockets.connect("ws://localhost:19000/v1/ws") as ws:
        await ws.send(json.dumps({"type": "connect", "client_type": "python"}))
        print(await ws.recv())  # {"type": "ack", ...}

        await ws.send(json.dumps({
            "type": "create_session",
            "agent_id": "researcher",
            "title": "Demo",
        }))
        print(await ws.recv())  # {"type": "session_created", ...}

        await ws.send(json.dumps({"type": "chat", "message": "Hello!"}))
        async for raw in ws:
            msg = json.loads(raw)
            if msg["type"] == "token":
                print(msg["text"], end="", flush=True)
            elif msg["type"] in ("done", "error"):
                print()
                break

asyncio.run(main())
```
