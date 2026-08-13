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
    ) -> "Agent": ...

    @classmethod
    async def connect(
        cls,
        server_url: str,
        *,
        auth_token: str | None = None,
        config: RemoteConfig | None = None,
    ) -> "Agent": ...

    async def run(
        self,
        prompt: str,
        *,
        session_id: str | None = None,
        images: list[ImageInput] | None = None,
        audio: list[AudioInput] | None = None,
    ) -> "AgentResult": ...

    async def stream(
        self,
        prompt: str,
        *,
        session_id: str | None = None,
    ) -> AsyncIterator[str]: ...

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

    def run_sync(self, prompt: str, *, session_id: str | None = None) -> "AgentResult": ...

    @property
    def memory(self) -> "Memory": ...
```

**Events:** `"token"`, `"done"`, `"error"`, `"tool_call"`, `"tool_result"`, `"start"`.

### `AgentResult`

```python
@dataclass(frozen=True)
class AgentResult:
    text: str
    session_id: str
    tool_calls: list[dict]
    metadata: dict
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
        agents: list[Agent] | None = None,
        *,
        spec: TeamSpec | None = None,
        enable_hitt: bool = False,
    ) -> "Team": ...

    async def spawn(self, prompt: str) -> "TeamResult": ...
    async def send(self, message: str, *, to: str | None = None) -> None: ...
    async def status(self) -> "TeamStatus": ...

@dataclass(frozen=True)
class TeamResult:
    output: str
    contributions: dict[str, str]
    session_id: str

@dataclass(frozen=True)
class TeamStatus:
    active_agents: list[str]
    completed: bool
    turn: int
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
class MemoryScope(enum.Enum):
    USER    = "user"
    SESSION = "session"
    GLOBAL  = "global"

class Memory:
    async def add(self, content: str, *, metadata: dict | None = None) -> str: ...
    async def search(self, query: str, *, top_k: int = 5) -> list["MemoryResult"]: ...
    async def delete(self, memory_id: str) -> None: ...
    async def list(self) -> list["MemoryResult"]: ...

@dataclass(frozen=True)
class MemoryResult:
    id: str
    content: str
    score: float
    metadata: dict
```

---

## Knowledge base and retrieval

```python
class KnowledgeBase:
    @classmethod
    async def create(
        cls,
        name: str,
        *,
        embedding_model: str = "text-embedding-3-small",
        vector_store: str = "chroma",
    ) -> "KnowledgeBase": ...

    async def add_documents(self, documents: list[str] | list[dict]) -> list[str]: ...
    async def query(self, query: str, *, top_k: int = 5) -> list["RetrievalResult"]: ...

class Retriever:
    def __init__(self, kb: KnowledgeBase, *, strategy: str = "hybrid") -> None: ...
    async def retrieve(self, query: str, *, top_k: int = 5) -> list["RetrievalResult"]: ...

class AgenticRetriever:
    def __init__(
        self,
        base_retriever: Retriever,
        *,
        llm: ModelConfig,
        max_rounds: int = 3,
        top_k_per_round: int = 5,
    ) -> None: ...
    async def retrieve(self, query: str) -> list["RetrievalResult"]: ...

class GraphKnowledgeBase:
    @classmethod
    async def create(cls, name: str) -> "GraphKnowledgeBase": ...
    async def add_documents(self, documents: list[str]) -> None: ...
    async def query(self, query: str, *, use_graph: bool = True, top_k: int = 5) -> list["RetrievalResult"]: ...

@dataclass(frozen=True)
class RetrievalResult:
    text: str
    score: float
    metadata: dict
```

---

## SwarmFlow

```python
def parallel(agents: list[Agent], prompt: str) -> SwarmFlowSpec: ...
def pipeline(agents: list[Agent], prompt: str) -> SwarmFlowSpec: ...
def phase(groups: list[SwarmFlowSpec]) -> SwarmFlowSpec: ...
async def run_swarmflow(spec: SwarmFlowSpec, *, prompt: str) -> "SwarmFlowResult": ...

@dataclass(frozen=True)
class SwarmFlowResult:
    output: str
    per_agent: dict[str, str]
```

---

## Evaluation

```python
@dataclass(frozen=True)
class EvalCase:
    input: str
    expected: str
    metadata: dict = field(default_factory=dict)

class Metric(Protocol):
    async def score(self, prediction: str, expected: str) -> float: ...

class ExactMatchMetric: ...
class LLMAsJudgeMetric:
    def __init__(self, model: ModelConfig | None = None) -> None: ...

class MetricEvaluator:
    def __init__(self, agent: Agent, metrics: list[Metric]) -> None: ...
    async def run(self, cases: list[EvalCase]) -> "EvalResult": ...

@dataclass(frozen=True)
class EvalResult:
    cases: list[dict]
    summary: dict[str, float]
```

---

## Observability

```python
@dataclass(frozen=True)
class OtelTracerConfig:
    service_name: str
    endpoint: str = "http://localhost:4317"
    insecure: bool = True
    resource_attributes: dict[str, str] = field(default_factory=dict)

def init_otel_tracer(config: OtelTracerConfig) -> None: ...
```

---

## Workspace

```python
class Workspace:
    def __init__(self, root: str | Path, *, sandbox: bool = False) -> None: ...
    def diff(self) -> str: ...
    @property
    def modified_files(self) -> list[Path]: ...
```

---

## Checkpoint backends

```python
class SessionStore(Protocol):
    async def save(self, session_id: str, data: dict) -> None: ...
    async def load(self, session_id: str) -> dict | None: ...
    async def delete(self, session_id: str) -> None: ...
    async def list(self) -> list[str]: ...

class CheckpointerBackend(Protocol):
    async def save_checkpoint(self, checkpoint_id: str, data: dict) -> None: ...
    async def load_checkpoint(self, checkpoint_id: str) -> dict | None: ...
    async def list_checkpoints(self) -> list[str]: ...

def register_store(name: str, cls: type[SessionStore]) -> None: ...
def register_checkpointer(name: str, cls: type[CheckpointerBackend]) -> None: ...
```

Built-in: `SqliteSessionStore`, `SqliteCheckpointer`.
Contrib: `PostgresSessionStore` (`sdk/contrib/postgres.py`), `S3Checkpointer` (`sdk/contrib/s3.py`).

---

## Multimodal

```python
@dataclass(frozen=True)
class ImageInput:
    content: bytes
    mime_type: str

    @classmethod
    def from_file(cls, path: str | Path) -> "ImageInput": ...
    @classmethod
    def from_url(cls, url: str) -> "ImageInput": ...

@dataclass(frozen=True)
class AudioInput:
    content: bytes
    mime_type: str

    @classmethod
    def from_file(cls, path: str | Path) -> "AudioInput": ...
```

---

## Multi-rollout

```python
@dataclass(frozen=True)
class MultiRolloutConfig:
    n: int = 4
    strategy: str = "best_of"   # "best_of" | "majority_vote"

class MultiRolloutExecutor:
    def __init__(self, agent: Agent, config: MultiRolloutConfig | None = None) -> None: ...
    async def run(self, prompt: str) -> list[AgentResult]: ...
    async def best_of(self, prompt: str, evaluator: MetricEvaluator) -> AgentResult: ...
```

---

## Context engine

```python
class ContextEngine:
    def __init__(self, processors: list[ContextProcessor]) -> None: ...
    @property
    def last_stats(self) -> dict: ...

class ToolResultBudgetProcessor:
    def __init__(self, max_chars: int = 4000) -> None: ...

class MessageSummaryOffloader:
    def __init__(self, threshold: int = 20) -> None: ...

class FullCompactProcessor: ...
class MicroCompactProcessor: ...
```

---

## Security rails

```python
class PermissionLevel(enum.Enum):
    ALLOW = "allow"
    DENY  = "deny"
    ASK   = "ask"

@dataclass(frozen=True)
class PermissionsSection:
    tool: str
    level: PermissionLevel
    host: "ApprovalHost | None" = None

class PermissionEngine:
    def __init__(self, sections: list[PermissionsSection]) -> None: ...

class CLIApprovalHost: ...     # prompts y/n on stdout

class ApprovalHost(Protocol):
    async def request_approval(self, tool_name: str, args: dict) -> bool: ...
```

---

## LSP integration

```python
# openjiuwen.sdk.lsp

async def initialize_lsp(server_cmd: list[str]) -> None: ...
def get_lsp_tool() -> SdkTool: ...
async def get_pending_lsp_diagnostics() -> list[dict]: ...
async def shutdown_lsp() -> None: ...
```

---

## Online RL

```python
@dataclass(frozen=True)
class RLConfig:
    algorithm: str = "ppo"
    lr: float = 1e-4
    batch_size: int = 8
    reward_threshold: float = 0.5

class RewardRegistry:
    def register(self, name: str, fn: Callable[["RolloutWithReward"], float]) -> None: ...
    def get(self, name: str) -> Callable: ...

@dataclass(frozen=True)
class RolloutWithReward:
    prompt: str
    outcome: str
    reward: float
    metadata: dict

class OnlineRLOptimizer:
    def __init__(self, config: RLConfig, reward_registry: RewardRegistry) -> None: ...
    def get_trajectories(self) -> list[RolloutWithReward]: ...

class OfflineRLOptimizer:
    def __init__(self, config: RLConfig, reward_registry: RewardRegistry) -> None: ...
    def export_trajectories(self, path: str) -> None: ...
```

---

## Builders

```python
class LlmAgentBuilder:
    def with_name(self, name: str) -> "LlmAgentBuilder": ...
    def with_model(self, model: ModelConfig) -> "LlmAgentBuilder": ...
    def with_tools(self, tools: list[SdkTool]) -> "LlmAgentBuilder": ...
    def with_memory(self, scope: MemoryScope) -> "LlmAgentBuilder": ...
    def with_knowledge_bases(self, kbs: list[KnowledgeBase]) -> "LlmAgentBuilder": ...
    async def build(self) -> Agent: ...

class WorkflowBuilder:
    def add_step(self, node: WorkflowNode) -> "WorkflowBuilder": ...
    def branch(self, condition: str, true_target: str, false_target: str) -> "WorkflowBuilder": ...
    def build(self) -> Workflow: ...
```

---

## Prompt builders

```python
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
├── ConnectionError
├── AuthError
├── SessionNotFoundError
├── ToolError
├── TimeoutError
├── ProtocolError
├── WorkflowError
├── A2AError
├── ServerError           carries .status_code
└── ConfigError
```

---

## TypeScript SDK

### `JiuwenSwarmClient`

```typescript
class JiuwenSwarmClient extends EventEmitter<ClientEvents> {
  constructor(config: ClientConfig)
  connect(): Promise<void>
  disconnect(): void
  get connected(): boolean
  readonly sessions: SessionManager
  send(message: string, options?: SendOptions): Promise<void>
  sendEnvelope(type: string, payload: unknown): void
}
```

### `ClientConfig`

```typescript
interface ClientConfig {
  url: string;
  authToken?: string;
  onToken?: (text: string) => void;
  onDone?: (sessionId: string) => void;
  onError?: (message: string) => void;
  onToolCall?: (call: ToolCallEnvelope) => Promise<string>;
  reconnect?: ReconnectConfig | false;
}

interface ReconnectConfig {
  maxAttempts?: number;
  initialDelayMs?: number;
  maxDelayMs?: number;
  factor?: number;
}
```

### `SessionManager`

```typescript
class SessionManager {
  list(): Promise<SessionInfo[]>
  create(title?: string, mode?: AgentMode): Promise<SessionInfo>
  setActive(id: string): void
  refresh(): Promise<void>
  get active(): SessionInfo | null
}
```

### Events

```typescript
type ClientEvents = {
  connected:    [];
  disconnected: [reason: string];
  token:        [text: string, sessionId: string];
  done:         [sessionId: string];
  error:        [message: string];
  reconnecting: [attempt: number, delayMs: number];
}
```

### `ToolCallEnvelope`

```typescript
interface ToolCallEnvelope {
  name: string;
  arguments: Record<string, unknown>;
  callId: string;
}
```

---

## REST API

Base URL: `http://localhost:19001`
Auth: `Authorization: Bearer <token>` (when auth is enabled on the server).

| Method | Path | Request body | Response |
|--------|------|-------------|----------|
| GET | `/v1/health` | — | `{status, version, protocol_version}` |
| GET | `/v1/sessions` | — | `{sessions: SessionInfo[]}` |
| POST | `/v1/sessions` | `{title, mode}` | `SessionInfo` |
| GET | `/v1/sessions/{id}` | — | `SessionInfo + {messages[]}` |
| DELETE | `/v1/sessions/{id}` | — | `204` |
| POST | `/v1/sessions/{id}/chat` | `{message}` | `{response}` |
| POST | `/v1/sessions/{id}/chat/stream` | `{message}` | SSE |
| GET | `/v1/agents` | — | `{agents: AgentInfo[]}` |
| GET | `/v1/agents/{id}` | — | `AgentInfo` |
| POST | `/v1/agents/{id}/run` | `{prompt}` | `{response}` |
| POST | `/v1/agents/{id}/stream` | `{prompt}` | SSE |
| GET | `/v1/tools` | — | `{tools: ToolInfo[]}` |
| POST | `/v1/knowledge` | `{name, embedding_model, vector_store}` | `{id}` |
| POST | `/v1/knowledge/{name}/documents` | `{documents[]}` | `{ids[]}` |
| POST | `/v1/knowledge/{name}/query` | `{query, top_k}` | `{results[]}` |
| POST | `/v1/eval/batch` | `{agent_id, metrics[], cases[]}` | `{results[], summary}` |
| POST | `/v1/agents/{id}/checkpoint` | `{session_id}` | `{checkpoint_id}` |
| GET | `/v1/checkpoints` | — | `{checkpoints[]}` |
| POST | `/v1/checkpoints/{id}/restore` | — | `{session_id, restored_from, message_count}` |

Interactive docs: `http://localhost:19001/docs`
