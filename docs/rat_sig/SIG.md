# System Investigation — JiuwenSwarm SDK

**Requirements reference:** `jiuwenswarm-sdk-RAT.md`

---

## Architecture Overview

The JiuwenSwarm SDK is three things that share one server runtime:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Developer's Application                          │
│                                                                         │
│  Python (in-process)   Python (remote)  TypeScript web  curl / any lang │
│  Agent.create()        Agent.connect()  @jiuwenswarm/sdk  REST API      │
│       │                     │                  │               │         │
│       │ (direct fn calls)   │ (WebSocket/HTTP) │  (WebSocket)  │ (HTTP)  │
└───────┼─────────────────────┼──────────────────┼───────────────┼─────────┘
        │                     │                  │               │
        │                     └──────────────────┘               │
        │                         connects to                     │
        ▼                              ▼                          ▼
┌───────────────────────┐   ┌──────────────────────────────────────────────┐
│  Runtime (in-process) │   │         JiuwenSwarm Server Process           │
│  openjiuwen.core +    │   │  openjiuwen.core + openjiuwen.harness        │
│  openjiuwen.harness   │   │  + openjiuwen.gateway (REST + WebSocket)     │
└───────────────────────┘   └──────────────────────────────────────────────┘
```

The key distinction:

- **`Agent.create()`** — runtime runs *inside* the caller's process.
  Uses `_RunnerBridge` to call `Runner` and `DeepAgent` directly.
  Requires `openjiuwen` installed. Takes `ModelConfig` (which LLM to use).

- **`Agent.connect()`** — runtime runs in a *separate server process*.
  Uses `_RemoteBridge` to speak the WebSocket envelope protocol or REST.
  Does not require the full runtime installed. Takes `RemoteConfig` (which server).
  This is exactly what the browser extension and mobile app do, now wrapped in Python.

```
┌─────────────────────────────────────────────────────────────────┐
│                   JiuwenSwarm Server Runtime                    │
│                                                                 │
│  openjiuwen.core           openjiuwen.harness                   │
│  ┌───────────┐             ┌──────────────────┐                 │
│  │  Runner   │◄────────────│   DeepAgent      │                 │
│  │ResourceMgr│             │   (task loop,    │                 │
│  └───────────┘             │    tools, rails) │                 │
│                            └──────────────────┘                 │
│  openjiuwen.core.single_agent                                   │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐              │
│  │ AgentCard  │   │  Session   │   │ ToolCard   │              │
│  └────────────┘   └────────────┘   └────────────┘              │
│                                                                 │
│  openjiuwen.agent_teams                                         │
│  ┌─────────────┐   ┌────────────┐   ┌──────────────────┐       │
│  │  TeamAgent  │   │ TeamSpec   │   │ RuntimePool      │       │
│  └─────────────┘   └────────────┘   └──────────────────┘       │
│                                                                 │
│  openjiuwen.gateway  (NEW)                                      │
│  ┌──────────────┐   ┌────────────┐   ┌──────────────────┐      │
│  │  REST routes │   │  WS router │   │  Auth middleware │      │
│  │  (FastAPI)   │   │ (Starlette)│   │                  │      │
│  └──────────────┘   └────────────┘   └──────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
           ▲                                     ▲
           │              existing               │
           │            connections              │
  IDE Plugin / JupyterLab             Browser Extension / Mobile
  (already use openjiuwen directly    (already use WebSocket protocol)
   or via WS — unchanged)
```

---

## Design Principles

1. **Thin façade, thick runtime.** The SDK is a layer of ergonomics over the
   existing `openjiuwen.core` and `openjiuwen.harness` modules. It adds no
   business logic; it only wraps, validates, and converts.

2. **No leaked internals.** `Runner`, `ResourceMgr`, `DeepAgent` config
   internals are not part of the public API. If they change, only the façade
   changes.

3. **Async-first, sync available.** Every Python SDK method is `async`. A
   `run_sync()` convenience wrapper handles the event loop for script users.

4. **Protocol stability over performance.** The WebSocket envelope format does
   not change without a version bump. Additive fields are safe; removals
   are not.

5. **Zero friction first run.** A developer should be able to go from
   `pip install` to a working agent in under 10 lines of code.

6. **TypeScript SDK mirrors Python SDK concepts, not internals.** The TS client
   doesn't know about `Runner` or `ResourceMgr`. It knows about sessions, agents,
   tools, and messages.

---

## Directory Layout

### Python SDK (`openjiuwen/sdk/`)

```
openjiuwen/
└── sdk/
    ├── __init__.py              # Public re-exports: Agent, Session, Tool, Team, tool, ModelConfig, RemoteConfig
    ├── agent.py                 # Agent façade class (in-process + remote)
    ├── session.py               # Session façade class
    ├── chat.py                  # Chat / message model
    ├── tools.py                 # @tool decorator + ToolResult
    ├── team.py                  # Team façade class
    ├── events.py                # EventEmitter mixin (on / off / emit)
    ├── config.py                # ModelConfig (in-process) + RemoteConfig (remote client)
    ├── errors.py                # SDK exception hierarchy
    └── _internal/
        ├── runner_bridge.py     # In-process: wraps Runner calls; converts to public types
        ├── session_bridge.py    # In-process: session CRUD via SessionManager
        ├── remote_bridge.py     # Remote: WebSocket/REST client calls to gateway
        └── sync_wrapper.py      # run_sync() event-loop management
```

### HTTP + WebSocket Gateway (`openjiuwen/gateway/`)

```
openjiuwen/
└── gateway/
    ├── __init__.py
    ├── app.py               # build_gateway_app() → FastAPI app
    ├── auth.py              # Bearer token middleware
    ├── rest/
    │   ├── __init__.py
    │   ├── sessions.py      # /v1/sessions routes
    │   ├── agents.py        # /v1/agents routes
    │   ├── tools.py         # /v1/tools routes
    │   └── health.py        # /v1/health route
    ├── ws/
    │   ├── __init__.py
    │   ├── router.py        # /v1/ws WebSocket handler
    │   ├── envelope.py      # Envelope parsing + validation
    │   └── dispatcher.py    # Routes envelopes to runtime handlers
    └── openapi/
        └── spec.py          # Additional OpenAPI customization
```

### TypeScript SDK (`packages/sdk/`)

```
packages/
└── sdk/
    ├── package.json         # name: @jiuwenswarm/sdk; dual CJS+ESM output
    ├── tsconfig.json
    ├── src/
    │   ├── index.ts         # Barrel export
    │   ├── client/
    │   │   ├── JiuwenSwarmClient.ts  # Main client class
    │   │   └── reconnect.ts          # Exponential back-off logic
    │   ├── protocol/
    │   │   ├── types.ts     # InboundEnvelope, OutboundEnvelope, SessionInfo, …
    │   │   ├── constants.ts # MSG object (token, done, error, sessions, …)
    │   │   └── validate.ts  # Runtime envelope shape checks
    │   ├── session/
    │   │   ├── SessionManager.ts
    │   │   └── types.ts
    │   ├── chat/
    │   │   ├── ChatManager.ts
    │   │   └── types.ts
    │   └── events/
    │       └── EventEmitter.ts   # Typed EventEmitter (no Node.js dep)
    └── tests/
        ├── client.test.ts
        ├── reconnect.test.ts
        └── session.test.ts
```

---

## Python SDK — Component Details

### `Agent` façade (`sdk/agent.py`)

The `Agent` class has two distinct constructors for the two execution modes.
Both return the same `Agent` type and expose the same `run`/`stream`/`on` API.
Internally they use different bridges: `_RunnerBridge` for in-process,
`_RemoteBridge` for remote.

```python
class Agent:

    # ── In-process constructor ────────────────────────────────────────────────
    # The runtime (DeepAgent, Runner) executes inside the caller's Python
    # process. No server URL needed. Requires openjiuwen runtime installed.
    @classmethod
    async def create(
        cls,
        name: str,
        *,
        model: ModelConfig | None = None,  # defaults to ModelConfig.from_env()
        tools: list[Tool] | None = None,
        workspace: Workspace | None = None,
        memory_scope: MemoryScope | None = None,
        knowledge_bases: list[KnowledgeBase] | None = None,
        event_handler: TaskLoopEventHandler | None = None,
        checkpoint_store: str | None = None,
        checkpoint_every: int | None = None,
    ) -> "Agent": ...

    # ── Remote constructor ────────────────────────────────────────────────────
    # The SDK connects to a running JiuwenSwarm server over WebSocket or REST.
    # The server manages the runtime and LLM credentials.
    # Equivalent to what the browser extension and mobile app do.
    @classmethod
    async def connect(
        cls,
        server_url: str,              # "ws://host:19000/v1/ws" or "http://host:19001"
        *,
        auth_token: str | None = None,
        config: RemoteConfig | None = None,
    ) -> "Agent": ...

    # ── Shared API (same regardless of mode) ─────────────────────────────────
    async def run(self, prompt: str, *, session_id: str | None = None) -> AgentResult: ...

    async def stream(
        self,
        prompt: str,
        *,
        session_id: str | None = None,
    ) -> AsyncIterator[str]: ...     # yields text tokens

    def on(self, event: str, callback: Callable) -> None: ...
    def off(self, event: str, callback: Callable) -> None: ...

    async def checkpoint(self) -> str: ...           # returns checkpoint ID
    @classmethod
    async def restore(cls, checkpoint_id: str, *, model: ModelConfig | None = None) -> "Agent": ...

    # Sync convenience (in-process only)
    def run_sync(self, prompt: str, *, session_id: str | None = None) -> AgentResult: ...
```

Events emitted: `"token"`, `"done"`, `"error"`, `"tool_call"`, `"tool_result"`.

---

### `Session` façade (`sdk/session.py`)

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

    async def history(self) -> list[ChatMessage]: ...
```

---

### `@tool` decorator (`sdk/tools.py`)

```python
@sdk.tool(name="fetch_url", description="Fetch a URL and return its text")
async def fetch_url(url: str) -> str:
    ...

# Equivalent to creating a ToolCard + Tool subclass manually.
# The decorator registers the function in the global tool registry.
```

---

### `Team` façade (`sdk/team.py`)

```python
class Team:
    @classmethod
    async def create(
        cls,
        spec: TeamSpec | None = None,
        *,
        agents: list[Agent] | None = None,
    ) -> "Team": ...

    async def spawn(self, prompt: str) -> TeamResult: ...
    async def send(self, message: str, *, to: str | None = None) -> None: ...
    async def status(self) -> TeamStatus: ...
```

---

### `ModelConfig` and `RemoteConfig` (`sdk/config.py`)

The config is split into two classes matching the two execution modes.

**In-process mode** — the runtime runs inside the developer's Python process.
No server URL. The developer configures which LLM provider and model to use.

```python
@dataclass(frozen=True)
class ModelConfig:
    """Configuration for in-process Agent.create()."""
    provider: str = "openai"           # "openai", "anthropic", "vllm", …
    model: str = "gpt-4o"
    api_key: str | None = None         # falls back to OPENAI_API_KEY / ANTHROPIC_API_KEY
    temperature: float | None = None
    max_tokens: int | None = None
    timeout: float = 60.0

    @classmethod
    def from_env(cls) -> "ModelConfig":
        """Reads JIUWENSWARM_MODEL, JIUWENSWARM_PROVIDER, OPENAI_API_KEY, etc."""
```

**Remote client mode** — the SDK connects to a separately running JiuwenSwarm
server (local or cloud) over WebSocket or REST. No model provider credentials
are needed on the client side; the server manages them.

```python
@dataclass(frozen=True)
class RemoteConfig:
    """Configuration for Agent.connect()."""
    server_url: str                    # "ws://host:19000/v1/ws" or "http://host:19001"
    auth_token: str | None = None
    timeout: float = 60.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> "RemoteConfig":
        """Reads JIUWENSWARM_URL, JIUWENSWARM_TOKEN."""
```

---

### Error hierarchy (`sdk/errors.py`)

```
SdkError
├── ConnectionError      # WebSocket / HTTP connection failed
├── AuthError            # 401 or token invalid
├── SessionNotFoundError # 404 on session ID
├── ToolError            # Tool invocation failed
├── TimeoutError         # Agent run exceeded timeout
└── ProtocolError        # Unexpected envelope shape
```

---

## HTTP Gateway — REST Routes

All routes are served by a FastAPI app mounted under `/v1/`. Auth is applied
globally via a `Bearer` token middleware (disabled when `auth_token = None` in
server config).

### Sessions

| Method | Path | Request body | Response |
|---|---|---|---|
| `GET` | `/v1/sessions` | — | `{sessions: SessionInfo[]}` |
| `POST` | `/v1/sessions` | `{title, mode}` | `SessionInfo` |
| `GET` | `/v1/sessions/{id}` | — | `SessionInfo + messages[]` |
| `DELETE` | `/v1/sessions/{id}` | — | `204 No Content` |

### Chat

| Method | Path | Request body | Response |
|---|---|---|---|
| `POST` | `/v1/sessions/{id}/chat` | `{message, notes?}` | `{response: string}` (blocking) |
| `POST` | `/v1/sessions/{id}/chat/stream` | `{message, notes?}` | `text/event-stream` SSE |

SSE event format:
```
event: token
data: {"text": "Hello"}

event: done
data: {"session_id": "abc123"}

event: error
data: {"message": "Model API error"}
```

### Agents

| Method | Path | Response |
|---|---|---|
| `GET` | `/v1/agents` | `{agents: AgentInfo[]}` |
| `GET` | `/v1/agents/{id}` | `AgentInfo` |
| `POST` | `/v1/agents/{id}/run` | `{response: string}` (blocking) |
| `POST` | `/v1/agents/{id}/stream` | SSE stream |

### Tools and Health

| Method | Path | Response |
|---|---|---|
| `GET` | `/v1/tools` | `{tools: ToolInfo[]}` |
| `GET` | `/v1/health` | `{status: "ok", version: "1.2.0", protocol_version: "1"}` |

### OpenAPI

FastAPI auto-generates the OpenAPI spec at `/docs` (Swagger UI) and
`/openapi.json`. The spec is the canonical REST API reference.

---

## WebSocket Gateway — Envelope Protocol (v1)

The WebSocket gateway is at `ws://<host>:19000/v1/ws`. It implements the same
envelope protocol already used by the browser extension, IDE plugin, and mobile
app — no changes to the envelope format — plus:

1. **Version in `ack`**: `{type: "ack", payload: {session_id, client_type, protocol_version: "1"}}`
2. **`client_type` support**: clients may send `{type: "connect", payload: {client_type: "sdk"}}`.
3. **All existing envelope types** (`chat`, `token`, `done`, `error`, `sessions`,
   `session_created`, `tool_call`, `tool_result`) are unchanged.

The gateway does not change the wire format. It adds the `/v1/ws` path prefix
and the `protocol_version` field in `ack` so clients can detect the versioned
gateway vs. the legacy direct connection.

---

## TypeScript SDK — Component Details

### `JiuwenSwarmClient`

```typescript
class JiuwenSwarmClient extends EventEmitter {
  constructor(config: ClientConfig) // { url, authToken?, onToken?, onDone?, onError? }

  connect(): Promise<void>
  disconnect(): void
  get connected(): boolean

  // Session management
  readonly sessions: SessionManager

  // Chat
  send(message: string, options?: SendOptions): Promise<void>

  // Raw protocol access
  sendEnvelope(type: string, payload: unknown): void
}
```

### `SessionManager`

```typescript
class SessionManager {
  list(): Promise<SessionInfo[]>
  create(title?: string, mode?: AgentMode): Promise<SessionInfo>
  setActive(id: string): void
  get active(): SessionInfo | null
  refresh(): Promise<void>
}
```

### `EventEmitter` (typed)

```typescript
type ClientEvents = {
  connected: [];
  disconnected: [reason: string];
  token: [text: string, sessionId: string];
  done: [sessionId: string];
  error: [message: string];
  reconnecting: [attempt: number, delayMs: number];
}

class EventEmitter<Events extends Record<string, unknown[]>> {
  on<K extends keyof Events>(event: K, listener: (...args: Events[K]) => void): this
  off<K extends keyof Events>(event: K, listener: (...args: Events[K]) => void): this
  emit<K extends keyof Events>(event: K, ...args: Events[K]): void
}
```

### Reconnect logic

```
connect() called
  │
  ▼
WebSocket opens
  │
  ├─ onopen → emit "connected"
  │
  └─ onclose → schedule reconnect
       │
       ▼
    delay: 1s → 2s → 5s → 10s → 30s (capped)
    if disconnect() was called: stop
       │
       ▼
    reopen WebSocket → repeat
```

---

## Sequence Diagrams

### Python SDK — `agent.stream(prompt)`

```
Developer           sdk.Agent            _RunnerBridge         openjiuwen.Runner
    │                    │                     │                      │
    │ await agent.stream │                     │                      │
    │ ("question")       │                     │                      │
    │───────────────────►│                     │                      │
    │                    │ bridge.stream_run() │                      │
    │                    │────────────────────►│                      │
    │                    │                     │ Runner.run_async()   │
    │                    │                     │─────────────────────►│
    │                    │                     │                      │ task loop…
    │                    │                     │◄─────────────────────│ token cb
    │                    │◄────────────────────│ yield "Hello"        │
    │◄───────────────────│                     │                      │
    │ "Hello"            │                     │                      │
    │     ·  ·  ·        │                     │                      │
    │                    │                     │◄─────────────────────│ done cb
    │                    │◄────────────────────│ StopAsyncIteration   │
    │◄───────────────────│                     │                      │
    │ (generator done)   │                     │                      │
```

### TypeScript SDK — `client.send(message)` with streaming

```
App                JiuwenSwarmClient         WS Server (gateway)
 │                        │                        │
 │ client.send("hello")   │                        │
 │───────────────────────►│                        │
 │                        │ sendEnvelope(chat, ...) │
 │                        │───────────────────────►│
 │                        │                        │ (runtime processes)
 │                        │◄───────────────────────│ token {"text":"Hi"}
 │                        │ emit("token", "Hi")    │
 │◄───────────────────────│                        │
 │ onToken("Hi")          │                        │
 │     ·  ·  ·            │                        │
 │                        │◄───────────────────────│ done {}
 │                        │ emit("done", id)       │
 │◄───────────────────────│                        │
 │ onDone(id)             │                        │
```

### REST API — SSE streaming (`curl` / any language)

```
curl (client)                     /v1/sessions/{id}/chat/stream
     │                                        │
     │ POST /v1/sessions/abc/chat/stream      │
     │ {"message": "Summarize this"}          │
     │───────────────────────────────────────►│
     │                                        │ (runtime processes)
     │◄───────────────────────────────────────│ event: token
     │ data: {"text": "The document"}         │ data: {"text": "The document"}
     │◄───────────────────────────────────────│ event: token
     │ data: {"text": " describes"}           │ data: {"text": " describes"}
     │     ·  ·  ·                            │
     │◄───────────────────────────────────────│ event: done
     │ data: {"session_id": "abc"}            │
     │                                        │
     (connection closes)
```

---

## Package Publishing

### Python SDK

```toml
# pyproject.toml addition (or separate distribution)
[project]
name = "openjiuwen-sdk"
version = "0.1.0"
description = "JiuwenSwarm agent SDK for Python"
requires-python = ">=3.11"
dependencies = [
    "openjiuwen",      # main runtime (same monorepo or PyPI dep)
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = ["pytest", "pytest-asyncio", "mypy"]
```

### TypeScript SDK

```json
{
  "name": "@jiuwenswarm/sdk",
  "version": "0.1.0",
  "description": "JiuwenSwarm client SDK for TypeScript",
  "main": "dist/index.cjs",
  "module": "dist/index.mjs",
  "types": "dist/index.d.ts",
  "exports": {
    ".": {
      "require": "./dist/index.cjs",
      "import": "./dist/index.mjs",
      "types": "./dist/index.d.ts"
    }
  },
  "peerDependencies": {
    "ws": ">=8.0.0"
  },
  "peerDependenciesMeta": {
    "ws": { "optional": true }
  }
}
```

`ws` is a peer dependency because browser environments use the native
`WebSocket` global; only Node.js callers need `ws`.

---

## Technical Constraints Summary

| Constraint | Mitigation |
|---|---|
| Existing WS clients must keep working | Gateway preserves envelope format; `/v1/ws` is additive |
| Python runtime is async | Façade is `async`; `run_sync()` wraps with `asyncio.run()` |
| TypeScript SDK must run in browser, Node, React Native | No DOM APIs; `ws` is optional peer dep; native `WebSocket` used when available |
| REST API versioning | All routes prefixed `/v1/`; breaking changes get `/v2/` prefix |
| Auth is optional in dev | `auth_token = None` bypasses middleware; enabled by default in prod config |
| No leaked internal classes | Façade converts to public dataclasses (`AgentResult`, `SessionInfo`, `ChatMessage`) |
| A2A server and REST gateway coexist | Mounted at different prefixes: A2A at `/a2a/`, REST at `/v1/` |
