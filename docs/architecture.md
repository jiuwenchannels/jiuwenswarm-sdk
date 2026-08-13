# Architecture

## Top-level structure

JiuwenSwarm is three SDKs that share one server runtime:

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        Developer's Application                          │
│                                                                         │
│  Python (in-process)   Python (remote)  TypeScript web  curl/any lang  │
│  Agent.create()        Agent.connect()  @jiuwenswarm/sdk  REST API     │
│       │                     │                  │               │        │
│       │ (direct fn calls)   │ (WebSocket/HTTP) │  (WebSocket)  │ (HTTP) │
└───────┼─────────────────────┼──────────────────┼───────────────┼────────┘
        │                     │                  │               │
        │                     └──────────────────┘               │
        │                         connects to                     │
        ▼                              ▼                          ▼
┌───────────────────────┐   ┌──────────────────────────────────────────┐
│  Runtime (in-process) │   │          JiuwenSwarm Server              │
│  openjiuwen.core +    │   │  openjiuwen.core + openjiuwen.harness   │
│  openjiuwen.harness   │   │  + openjiuwen.gateway (REST + WS)       │
└───────────────────────┘   └──────────────────────────────────────────┘
```

---

## Design principles

1. **Thin façade, thick runtime.** The SDK adds no business logic — it
   wraps, validates, and converts. All execution lives in `openjiuwen.core`
   and `openjiuwen.harness`.

2. **No leaked internals.** `Runner`, `ResourceMgr`, `DeepAgent` internals
   are not part of the public API. If they change, only the bridge changes.

3. **Async-first, sync available.** Every Python SDK method is `async`.
   `run_sync()` wraps the event loop for script users.

4. **Protocol stability over performance.** The WebSocket envelope format
   does not change without a version bump. Additive fields are safe;
   removals are not.

5. **Zero friction first run.** `pip install` to a working streaming agent
   in under 10 lines.

6. **TypeScript mirrors Python concepts, not internals.** The TS client
   knows about sessions, agents, tools, and messages — not `Runner` or
   `ResourceMgr`.

---

## Python SDK layer

### Façade → Bridge → Runtime

```
openjiuwen/sdk/                    openjiuwen/sdk/_internal/          openjiuwen.core/.harness
─────────────────────────          ───────────────────────────        ──────────────────────────
agent.py       (Agent)      ────►  runner_bridge.py          ────►   Runner, DeepAgent
session.py     (Session)    ────►  session_bridge.py         ────►   SessionManager
team.py        (Team)       ────►  team_bridge.py            ────►   TeamAgent, RuntimePool
workflow.py    (Workflow)   ────►  workflow_bridge.py        ────►   workflow runtime
a2a.py         (RemoteAgent)────►  remote_bridge.py          ────►   HTTP/WS to A2A server
```

All bridges use **module-level wrapper functions** (not class methods).
Tests replace them with `monkeypatch.setattr` — no mocking of runtime
class instantiation required.

```python
# _internal/runner_bridge.py

# Module-level — patchable in tests
async def run_agent(card, prompt: str, session_id: str | None) -> str:
    runner = Runner.get()
    return await runner.run(card, prompt, session_id)

# Façade calls through the module reference
import openjiuwen.sdk._internal.runner_bridge as _rb

class Agent:
    async def run(self, prompt: str) -> AgentResult:
        raw = await _rb.run_agent(self._card, prompt, self._session_id)
        return AgentResult(text=raw)
```

### Bridge modules

| Module | Wraps | Key functions |
|--------|-------|---------------|
| `runner_bridge.py` | `openjiuwen.core.Runner` | `make_agent_card`, `run_agent`, `stream_agent`, `checkpoint_agent`, `restore_agent` |
| `session_bridge.py` | `openjiuwen.core.SessionManager` | `create_session`, `list_sessions`, `get_session`, `delete_session`, `get_history` |
| `team_bridge.py` | harness team runtime | `make_team_card`, `create_team_session`, `spawn_team`, `send_team_message`, `team_status` |
| `workflow_bridge.py` | workflow runtime | `make_workflow_card`, `build_runtime_workflow`, `run_workflow`, `stream_workflow` |
| `remote_bridge.py` | WebSocket / REST | `connect_remote`, `run_remote`, `stream_remote` (used by `Agent.connect()`) |
| `sync_wrapper.py` | Python event loop | `run_sync(coro)` — new loop; raises if called from running loop |

### Card / Config split

- **Cards** (`AgentCard`, `WorkflowCard`, `TeamCard`) — frozen dataclasses
  defining identity and metadata. Created once inside the bridge, never
  exposed to application code.
- **Configs** (`ModelConfig`, `RemoteConfig`) — frozen dataclasses for
  runtime knobs. Created by application code, forwarded to the bridge.

### Public API contract

Every type in a public method signature must be defined in
`openjiuwen/sdk/`. Bridge functions return plain dicts or strings; the
façade wraps them in SDK dataclasses (`AgentResult`, `SessionInfo`,
`WorkflowResult`, …).

### EventEmitter and Hooks

`EventEmitter` (`sdk/events.py`) is a standalone typed pub/sub:

- `emit(name, *args)` schedules async callbacks on the running loop via
  `asyncio.ensure_future`.
- `emit_async(name, *args)` awaits all callbacks in registration order.

`Hooks` (`sdk/hooks.py`) holds lists of callbacks for six named events.
`hooks.wire(emitter)` registers them all into an `EventEmitter`.
`Agent.create(hooks=hooks)` calls `wire` after agent initialisation.

`TaskLoopEventHandler` is the full-featured variant: a class with
lifecycle methods that receive typed arguments and can intercept tool
calls by returning a `ToolResult` early.

### Dependency rules

```
openjiuwen/sdk/          may import: sdk/_internal/, sdk/*.py
openjiuwen/sdk/_internal/  may import: openjiuwen.core, openjiuwen.harness
openjiuwen/sdk/          must NOT import directly from openjiuwen.core or .harness
```

Circular imports between `sdk/` modules are forbidden. Use `TYPE_CHECKING`
guards for type-only cross-references.

---

## HTTP + WebSocket Gateway

```
openjiuwen/gateway/
├── app.py            build_gateway_app(config: GatewayConfig) → FastAPI
├── auth.py           BearerTokenMiddleware — 401 when enabled, no-op otherwise
├── rest/
│   ├── health.py     GET /v1/health
│   ├── sessions.py   /v1/sessions  CRUD + /chat + /chat/stream
│   ├── agents.py     /v1/agents  list + /run + /stream
│   ├── tools.py      GET /v1/tools
│   ├── knowledge.py  /v1/knowledge  create + /documents + /query
│   ├── eval.py       POST /v1/eval/batch
│   └── checkpoints.py  checkpoint, list, restore
└── ws/
    ├── router.py     /v1/ws  WebSocket handler
    ├── envelope.py   parse + validate JSON-RPC envelopes
    └── dispatcher.py route envelopes to runtime; add protocol_version to ack
```

The gateway mounts A2A routes at `/a2a/` (separate prefix from REST
at `/v1/`), allowing both to coexist on the same server process.

### REST route table

| Method | Path | Description |
|--------|------|-------------|
| GET | `/v1/health` | `{"status":"ok","version":"...","protocol_version":"1"}` |
| GET | `/v1/sessions` | `{sessions: SessionInfo[]}` |
| POST | `/v1/sessions` | `{title, mode}` → `SessionInfo` |
| GET | `/v1/sessions/{id}` | `SessionInfo + messages[]` |
| DELETE | `/v1/sessions/{id}` | `204 No Content` |
| POST | `/v1/sessions/{id}/chat` | Blocking → `{response: string}` |
| POST | `/v1/sessions/{id}/chat/stream` | SSE → `event: token / done / error` |
| GET | `/v1/agents` | `{agents: AgentInfo[]}` |
| GET | `/v1/agents/{id}` | `AgentInfo` |
| POST | `/v1/agents/{id}/run` | Blocking run |
| POST | `/v1/agents/{id}/stream` | SSE run |
| GET | `/v1/tools` | `{tools: ToolInfo[]}` |
| POST | `/v1/knowledge` | Create knowledge base |
| POST | `/v1/knowledge/{name}/documents` | Add documents |
| POST | `/v1/knowledge/{name}/query` | Query KB |
| POST | `/v1/eval/batch` | Batch evaluation |
| POST | `/v1/agents/{id}/checkpoint` | Save checkpoint |
| GET | `/v1/checkpoints` | List checkpoints |
| POST | `/v1/checkpoints/{id}/restore` | Restore checkpoint |

FastAPI auto-generates OpenAPI at `/docs` and `/openapi.json`.

### WebSocket envelope protocol (v1)

The gateway at `ws://host:19000/v1/ws` implements the same envelope
format used by the browser extension, IDE plugin, and mobile app — with
two additive extensions:

1. `ack` payload includes `"protocol_version": "1"`.
2. `connect` envelope may include `"client_type": "sdk"`.

All existing envelope types (`chat`, `token`, `done`, `error`,
`sessions`, `session_created`, `tool_call`, `tool_result`) are unchanged.

### SSE event format

```
event: token
data: {"text": "Hello"}

event: done
data: {"session_id": "abc123"}

event: error
data: {"message": "Model API error"}
```

---

## TypeScript SDK layer

```
packages/sdk/src/
├── index.ts                      barrel export
├── client/
│   ├── JiuwenSwarmClient.ts      main client class
│   └── reconnect.ts              ReconnectScheduler (1→2→5→10→30 s, capped)
├── session/
│   ├── SessionManager.ts
│   └── types.ts                  SessionInfo, AgentMode
├── protocol/
│   ├── types.ts                  InboundEnvelope, OutboundEnvelope, ChatMessage
│   ├── constants.ts              MSG object
│   └── validate.ts               parseEnvelope(raw) → typed or ProtocolError
└── events/
    └── EventEmitter.ts           typed, no Node.js dependency
```

### `JiuwenSwarmClient` lifecycle

```
connect() called
    │
    ▼
WebSocket opens ──────────────────────────► emit "connected"
    │
    └─► onclose ──► ReconnectScheduler
                        │
                        ▼
                    delay: 1s → 2s → 5s → 10s → 30s (capped)
                    if disconnect() called: stop
                        │
                        ▼
                    reopen WebSocket ──────► repeat
```

### WebSocket detection

1. If `globalThis.WebSocket` exists (browser / React Native) — use it.
2. Else if `ws` npm package is installed — use it (Node.js).
3. Else — throw `ConnectionError`.

`ws` is an optional peer dependency. Browser environments need no extra
package.

### TypeScript EventEmitter

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

### Tool call interception

By default, any `tool_call` envelope from the server is rejected with
`{error: "not supported"}`. Supply `onToolCall` to handle it client-side:

```typescript
const client = new JiuwenSwarmClient({
  url: "ws://localhost:19000/v1/ws",
  onToolCall: async (call) => {
    if (call.name === "get_location") {
      const pos = await navigator.geolocation.getCurrentPosition(…);
      return JSON.stringify({ lat: pos.coords.latitude, … });
    }
    throw new Error(`Not implemented: ${call.name}`);
  },
});
```

### Package distribution

```json
{
  "name": "@jiuwenswarm/sdk",
  "main":    "dist/index.cjs",
  "module":  "dist/index.mjs",
  "types":   "dist/index.d.ts",
  "exports": {
    ".": {
      "require": "./dist/index.cjs",
      "import":  "./dist/index.mjs",
      "types":   "./dist/index.d.ts"
    }
  },
  "peerDependencies": { "ws": ">=8.0.0" },
  "peerDependenciesMeta": { "ws": { "optional": true } }
}
```

---

## Sequence diagrams

### Python in-process — `agent.stream(prompt)`

```
App                sdk.Agent            runner_bridge         openjiuwen.Runner
 │                     │                     │                      │
 │  await agent.stream │                     │                      │
 │──────────────────► │                     │                      │
 │                    │  _rb.stream_agent() │                      │
 │                    │────────────────────►│                      │
 │                    │                     │  Runner.run_async()  │
 │                    │                     │─────────────────────►│
 │                    │                     │                      │ task loop
 │                    │◄────────────────────│ yield "Hello"        │ token cb
 │◄───────────────────│                     │                      │
 │  "Hello"           │                     │                      │
 │    · · ·           │                     │◄─────────────────────│ done cb
 │◄───────────────────│◄────────────────────│ StopAsyncIteration   │
 │  (generator done)  │                     │                      │
```

### TypeScript SDK — `client.send(message)` with streaming

```
App                 JiuwenSwarmClient          WS Gateway
 │                          │                      │
 │  client.send("hello")    │                      │
 │─────────────────────────►│                      │
 │                          │  sendEnvelope(chat)  │
 │                          │─────────────────────►│
 │                          │                      │ (runtime)
 │                          │◄─────────────────────│ token {"text":"Hi"}
 │◄─────────────────────────│  emit("token","Hi")  │
 │  onToken("Hi")           │                      │
 │    · · ·                 │◄─────────────────────│ done {}
 │◄─────────────────────────│  emit("done", id)    │
 │  onDone(id)              │                      │
```

### REST — SSE streaming

```
curl / client                      /v1/sessions/{id}/chat/stream
    │                                        │
    │  POST {"message":"Summarise this"}     │
    │───────────────────────────────────────►│
    │                                        │ (runtime)
    │◄───────────────────────────────────────│ event: token
    │  data: {"text": "The document"}        │
    │◄───────────────────────────────────────│ event: token
    │  data: {"text": " describes"}          │
    │    · · ·                               │
    │◄───────────────────────────────────────│ event: done
    │  data: {"session_id": "abc"}           │
    │  (connection closes)                   │
```

---

## Technical constraints

| Constraint | Resolution |
|------------|------------|
| Existing WS clients must keep working | Gateway preserves envelope format; `/v1/ws` is additive |
| Python runtime is async | Façade is `async`; `run_sync()` wraps with a new event loop |
| TS SDK must run in browser, Node.js, React Native | No DOM APIs; `ws` is optional peer dep |
| REST API versioning | All routes at `/v1/`; breaking changes use `/v2/` |
| Auth is optional in dev | `auth_token=None` bypasses middleware |
| No leaked internal classes | Bridges convert to SDK dataclasses before returning |
| A2A and REST coexist | A2A at `/a2a/`, REST at `/v1/` — separate mount prefixes |
