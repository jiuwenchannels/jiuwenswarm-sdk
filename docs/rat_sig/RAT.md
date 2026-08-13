# Requirements Analysis — JiuwenSwarm SDK

---

## Source of Demand

- **Strategic Direction** — Platform / API Product Surface
- **Product Requirements** — JiuwenSwarm Platform / Developer Ecosystem

---

## Demand Background

### WHY

JiuwenSwarm is currently available only as finished applications: a browser
extension, an IDE plugin, a JupyterLab extension, and a mobile app. Each of
these is built on top of the same Python runtime and WebSocket protocol, but
that runtime is not accessible to external developers. The result is a walled
garden: a developer who wants to embed a JiuwenSwarm research agent in their
own product, automate agent runs in a CI pipeline, or build a vertical SaaS on
top of the platform has no supported path to do so.

An SDK changes this. It turns JiuwenSwarm from a consumer application into a
platform that other products can build on. The addressable audience widens from
individual power users to the entire community of developers and companies who
want an AI agent with serious capabilities (code execution, browser context,
long-term memory, multi-agent coordination) without building that infrastructure
from scratch.

Three developer audiences are distinct enough to warrant separate API surfaces:

**Audience 1 — Python developers (data scientists, ML engineers, automation
engineers):** Want to call a JiuwenSwarm agent from a Python script, notebook,
or server. They are comfortable with pip packages. They want `async/await`,
type hints, streaming callbacks, and the ability to plug in custom tools.

**Audience 2 — Web and mobile developers (TypeScript/JavaScript):** Building
applications on top of JiuwenSwarm — web dashboards, mobile apps, internal
tools. They want an npm package that handles the WebSocket protocol, session
management, streaming, and reconnection. They do not want to understand the
binary protocol.

**Audience 3 — Polyglot developers / language-agnostic integrations:** Building
in Go, Rust, Java, or any language that cannot import a Python package. They
need a stable HTTP REST API and a WebSocket API that is documented well enough
to write a client in any language.

### WHEN

The existing codebase (`openjiuwen/core`, `openjiuwen/harness`) already
contains most of the logic needed for an SDK. The Python package (`openjiuwen`)
is installable today. The gap is: (1) the public API boundary is not defined —
`core/__init__.py` exports nothing; (2) there is no TypeScript client package;
(3) there is no formally documented REST or WebSocket gateway.

SDK work can begin immediately alongside the mobile app. It does not require
cloud hosting — developers can run a local server and call the SDK against it.
Production distribution requires a stable API version and a cloud endpoint, but
those are later phases.

### WHAT

Three SDK components, delivered in sequence:

---

**Component 1 — Python SDK (`openjiuwen-sdk` package)**

A well-defined, stable public API layer over the existing `openjiuwen` runtime.
Developers `pip install openjiuwen-sdk` (or install the existing `openjiuwen`
package) and can:

- Create and run agents programmatically (`create_agent`, `run`, `stream`)
- Manage sessions (`Session.create`, `.list`, `.get`, `.delete`)
- Register custom tools (`@tool` decorator or `ToolCard` API)
- Use the multi-agent team API (`Team.create`, `.spawn`, `.send`)
- Hook into the task loop via event callbacks
- Checkpoint and restore sessions

| Capability | Existing class | SDK surface |
|---|---|---|
| Create and run an agent | `DeepAgent`, `Runner` | `Agent.create()`, `agent.run(prompt)`, `agent.stream(prompt)` |
| Session management | `AgentSession`, `SessionManager` | `Session.create()`, `.list()`, `.get()` |
| Custom tools | `Tool`, `ToolCard` | `@sdk.tool` decorator |
| Multi-agent team | `TeamAgent`, `TeamAgentSpec` | `Team.create()`, `.spawn()` |
| Event hooks | `TaskLoopEventHandler` | `agent.on("token", cb)`, `.on("done", cb)` |
| Checkpointing | `extensions/checkpointer` | `agent.checkpoint()`, `Agent.restore(id)` |

---

**Component 2 — TypeScript / JavaScript SDK (`@jiuwenswarm/sdk` npm package)**

A browser- and Node.js-compatible npm package that implements the JiuwenSwarm
WebSocket protocol. The mobile app, web app, browser extension, and IDE plugin
all currently implement this protocol independently. The TypeScript SDK
eliminates that duplication.

| Capability | Description |
|---|---|
| `JiuwenSwarmClient` | Opens WebSocket to a JiuwenSwarm server; handles `ack`, `token`, `done`, `error`, `sessions` envelopes |
| Session management | `client.sessions.list()`, `.create()`, `.setActive()` |
| Streaming chat | `client.chat.send(text, mode)` — returns async iterator of tokens |
| Tool call rejection | Automatically responds to `tool_call` with `{error: "not supported"}` for clients that don't implement tools |
| Reconnection | Exponential back-off (1→2→5→10→30 s); `AppState` / `visibilitychange` foreground reconnect |
| Event emitter | `client.on("connected")`, `.on("token", cb)`, `.on("done", cb)`, `.on("error", cb)` |
| Typed envelopes | Full TypeScript types for all protocol messages |

---

**Component 3 — HTTP REST API + WebSocket API (server-side gateway)**

A formally documented and versioned HTTP + WebSocket gateway embedded in the
JiuwenSwarm server. Developers in any language can call it without a language SDK.

| Endpoint | Method | Description |
|---|---|---|
| `/v1/sessions` | GET | List sessions |
| `/v1/sessions` | POST | Create session |
| `/v1/sessions/{id}` | GET | Get session (messages, metadata) |
| `/v1/sessions/{id}` | DELETE | Delete session |
| `/v1/sessions/{id}/chat` | POST | Send message (non-streaming) |
| `/v1/sessions/{id}/chat/stream` | POST | Send message (SSE streaming) |
| `/v1/agents` | GET | List registered agents |
| `/v1/agents/{id}/run` | POST | Run agent one-shot (non-streaming) |
| `/v1/agents/{id}/stream` | POST | Run agent with SSE streaming |
| `/v1/tools` | GET | List registered tools |
| `/v1/health` | GET | Server health / version |
| `ws://.../v1/ws` | WebSocket | Full-duplex protocol (existing envelope format, now versioned) |

---

### Requirement Type

☑ **Functionality** (new developer-facing API surface)
☑ **Operation and Maintenance Methods** (versioning, changelog, deprecation policy)
☑ **Compatibility** (existing clients — browser extension, IDE plugin, mobile — must continue to work unchanged)

---

## Needs Assessment

### Requirement Decomposition

| Sub-requirement | Scope |
|---|---|
| Define Python public API boundary | `openjiuwen/core/__init__.py`, `openjiuwen/harness/__init__.py` |
| `Agent` façade class (create, run, stream) | `openjiuwen/sdk/agent.py` |
| `Session` façade class (CRUD, history) | `openjiuwen/sdk/session.py` |
| `@tool` decorator and `ToolCard` convenience | `openjiuwen/sdk/tools.py` |
| `Team` façade class (create, spawn, send) | `openjiuwen/sdk/team.py` |
| Event emitter mixin for Python SDK | `openjiuwen/sdk/events.py` |
| Python SDK package metadata and entry points | `pyproject.toml` + `openjiuwen/sdk/__init__.py` |
| HTTP REST gateway (FastAPI) | `openjiuwen/gateway/rest/` |
| WebSocket gateway (versioned, with `client_type`) | `openjiuwen/gateway/ws/` |
| OpenAPI spec generation (from FastAPI) | auto-generated via `/docs` endpoint |
| TypeScript envelope types | `packages/sdk/src/protocol/types.ts` |
| TypeScript `JiuwenSwarmClient` class | `packages/sdk/src/client/JiuwenSwarmClient.ts` |
| TypeScript session and chat managers | `packages/sdk/src/session/`, `packages/sdk/src/chat/` |
| TypeScript reconnection logic | `packages/sdk/src/client/reconnect.ts` |
| npm package build and publish config | `packages/sdk/package.json`, `tsconfig.json` |
| Python SDK documentation (docstrings + mkdocs) | `docs/sdk/python/` |
| TypeScript SDK documentation (typedoc) | `docs/sdk/typescript/` |
| REST API reference (auto-generated OpenAPI) | `docs/sdk/rest/` |
| Migration guide for existing clients | `docs/sdk/migration.md` |
| Python SDK unit tests | `tests/unit_tests/sdk/` |
| TypeScript SDK unit tests | `packages/sdk/tests/` |
| Integration tests (Python SDK → real server) | `tests/system_tests/sdk/` |
| Version policy and changelog | `CHANGELOG.md`, `docs/sdk/versioning.md` |

---

### Constraints

**Backward compatibility with existing clients:**
The browser extension, IDE plugin, JupyterLab extension, and mobile app all
speak the existing WebSocket envelope protocol. The WebSocket gateway must
remain backward-compatible: adding fields is safe; removing or renaming
fields is a breaking change requiring a new version prefix.

**Python version and typing:**
The SDK targets Python 3.11+. All public functions must be annotated with type
hints. The `openjiuwen` package already uses modern Python 3.9+ generics; the
SDK layer must not regress this.

**Async-first, sync convenience:**
The existing runtime is async (`asyncio`). The Python SDK must be async-first.
A sync convenience wrapper (`agent.run_sync(prompt)`) should be provided for
script users who do not want to manage an event loop.

**No bundled LLM credentials:**
The SDK does not ship with or manage LLM API keys. The developer is responsible
for configuring the underlying model (via environment variables or config file).
The SDK must make this configuration surface explicit and documented.

**TypeScript SDK: browser and Node.js parity:**
The `@jiuwenswarm/sdk` package must work in a browser (using the native
`WebSocket` API), in Node.js (using the `ws` package as a ponyfill), and in
React Native (using the React Native `WebSocket` API). No DOM-specific APIs.

**REST API versioning:**
All REST routes are prefixed with `/v1/`. When a breaking change is introduced,
a `/v2/` prefix is added. The previous version remains active for at least one
major release cycle. Version is also returned in `/v1/health`.

**Authentication:**
The REST and WebSocket APIs accept an optional `Authorization: Bearer <token>`
header. In local development mode, authentication can be disabled. The Python
SDK transparently passes the configured auth token.

**No shipping of agent-core internals as public API:**
The SDK façade must not leak internal classes (`Runner`, `ResourceMgr`,
`DeepAgent` config internals) into the public API. If an internal detail changes,
only the façade changes — not the developer's code.

---

### Impact on Existing Systems

**`openjiuwen/core/__init__.py` and `openjiuwen/harness/__init__.py`:**
Currently export very little. The SDK phase defines what is public. These
`__init__.py` files become the authoritative export list. Internal modules are
not re-exported.

**WebSocket gateway (`jiuwenswarm-browser`, mobile, IDE, JupyterLab):**
The existing protocol continues to work unchanged. The gateway adds a version
field to the `ack` envelope (`"protocol_version": "1"`) and adds optional
`client_type` handling. No existing client needs to change to continue working.

**A2A extension (`openjiuwen/extensions/a2a`):**
The REST gateway and A2A server are complementary. A2A is agent-to-agent
communication (internal orchestration). The REST gateway is developer-facing
(external API). They share the same underlying runtime but serve different
audiences.

**MCP server (`openjiuwen/agent_teams/mcp`):**
Unchanged. MCP is for team coordination over stdio; the SDK does not wrap MCP.

**`pyproject.toml`:**
The `openjiuwen-sdk` package can be a sub-package of the existing `openjiuwen`
namespace (`openjiuwen.sdk`) or published as a separate distribution. For v1,
it lives inside the same monorepo as a namespace sub-package.

---

### External Dependencies

| Dependency | Purpose | Notes |
|---|---|---|
| `fastapi` | REST gateway HTTP server | Already a transitive dependency via agent_evolving gateway |
| `uvicorn` | ASGI server for FastAPI | Already present in the codebase |
| `starlette` | WebSocket handling, SSE streaming | Already used in A2A server |
| `pydantic` | Request/response schema validation | Already used throughout core |
| `mkdocs` + `mkdocstrings` | Python SDK documentation generation | New dev dependency |
| `TypeDoc` | TypeScript SDK documentation generation | New, in `packages/sdk` |
| `tsup` or `esbuild` | TypeScript SDK build (CJS + ESM dual output) | New, in `packages/sdk` |
| `ws` (npm) | Node.js WebSocket ponyfill for TypeScript SDK | New, peer dependency |
| `vitest` | TypeScript SDK unit tests | New, in `packages/sdk` |
