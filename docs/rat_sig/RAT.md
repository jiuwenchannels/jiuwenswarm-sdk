# Requirements Analysis — JiuwenSwarm SDK

---

## Source of Demand

- **Strategic Direction** — Platform / API Product Surface
- **Product Requirements** — JiuwenSwarm Platform / Developer Ecosystem

---

## Demand Background

### WHY

#### The problem: what people cannot do today

JiuwenSwarm ships only as finished applications — a browser extension, an IDE
plugin, a JupyterLab extension, and a mobile app. All of them are built on the
same Python runtime and WebSocket protocol, but that runtime is deliberately
invisible to the outside. For a developer this means three concrete dead ends:

- **They cannot embed the agent in their own product.** A SaaS company that
  wants to add "a JiuwenSwarm agent" to their web app has no supported entry
  point — the runtime is not importable, the protocol is undocumented, and there
  is no stable API to call.
- **They cannot automate agent runs.** A team that wants to run agents in a CI
  pipeline, a nightly job, or a batch of experiments has no way to trigger a run
  programmatically; today the only path is a human clicking in a finished UI.
- **They cannot build on top of it.** A startup that wants to build a vertical
  agent product on JiuwenSwarm's capabilities (code execution, browser context,
  long-term memory, multi-agent coordination) has to either reverse-engineer a
  private protocol — unsupported, brittle — or give up.

Without an SDK these developers do not simply "have a worse time": they go
elsewhere. Every one of these jobs today ends in one of two outcomes — (a) the
team abandons JiuwenSwarm for a competitor with an SDK, or (b) they build on a
fragile, undocumented protocol that breaks on the next release and generates
support burden. Either way, JiuwenSwarm loses a paying developer without gaining
anything.

#### The value: what the SDK unlocks

The SDK removes the wall. Each of the dead ends above becomes a short, supported
code path:

- **Embed:** `pip install openjiuwen-sdk` + a handful of lines gives a working
  agent with code execution, browser context, and long-term memory — the
  capabilities JiuwenSwarm already has, now callable from any product.
- **Automate:** `agent.run(prompt)` in a script, notebook, or server turns agent
  invocation into an ordinary function call — schedulable, testable, and
  composable in CI or batch pipelines.
- **Build on:** a stable, versioned, documented API makes JiuwenSwarm a platform
  rather than a black box, so third parties can ship vertical products on it
  without reverse-engineering anything.

The critical "rather than not do" argument is the infrastructure: JiuwenSwarm
already owns the hard parts — code execution sandboxing, browser context,
long-term memory, multi-agent coordination. That is precisely the infrastructure
every competitor would otherwise have to build from scratch. The SDK is the only
supported way to *get* that infrastructure programmatically, which is why a
developer who needs a serious agent chooses it over raw model APIs or
re-implementing everything themselves.

#### The stakes for JiuwenSwarm: why build it now

Developer value alone is not the reason to build; it is the reason the product
*can* win. The business case is what JiuwenSwarm gains and loses by the decision.

**The return to JiuwenSwarm.** An SDK converts one-time consumers into an
ecosystem. Every developer who builds on the SDK is locked into the runtime for
the life of their product: they depend on JiuwenSwarm's capabilities, sessions,
and semantics, so they stay, upgrade, and pay. Each embedded agent is
distribution — a JiuwenSwarm-powered feature inside a third-party product that
acquires and retains users for us without our sales effort. A platform with a
growing developer base also compounds: more builders ship more agent products,
which normalizes JiuwenSwarm as the default, which attracts more builders. The
SDK is the difference between selling a finished app and owning a category.

**Competitive position and timing.** The agent market is at the exact moment
where SDKs are being chosen — OpenAI and Anthropic expose model APIs,
LangChain/LangGraph, CrewAI, and AutoGen sell orchestration, and Claude Code
ships an SDK. None of them bundle JiuwenSwarm's combination of sandboxed code
execution, browser context, long-term memory, and multi-agent coordination
behind a clean API. That is a window, and windows close: every month JiuwenSwarm
stays a walled garden, developers who need these capabilities pick another
vendor and, once integrated, rarely migrate. Shipping the SDK now captures the
developers who are deciding today; shipping later means competing for
developers who already chose elsewhere. The cost of waiting is the permanent
loss of a cohort.

**What winning looks like.** The SDK is successful when it measurably moves the
platform, not when it merely exists. The concrete success criteria are: (a)
adoption — developers install and run agents through the SDK outside the shipped
apps, tracked as SDK-driven sessions distinct from UI sessions; (b) retention
and lock-in — SDK-built products keep running JiuwenSwarm across releases
without migration, tracked as recurring SDK usage; (c) ecosystem — third-party
products ship on the SDK and are attributable to it; (d) revenue — SDK usage
correlates with paid seats or platform consumption. If those move, the SDK paid
for itself many times over; if none move, the SDK is just another package, and
that failure is detectable early rather than assumed.

#### The three audiences, and what each is trying to do

Three developer audiences are distinct enough to warrant separate API surfaces.
For each, the SDK answers a specific job-to-be-done, not just a preference:

**Audience 1 — Python developers (data scientists, ML engineers, automation
engineers).** Their job is running agents inside their own compute: notebooks,
batch experiments, evaluation harnesses, CI jobs. They need a pip package with
`async/await`, type hints, streaming callbacks, and custom-tool plug-in — so an
agent run is a function they can call, not a UI they have to click.

**Audience 2 — Web and mobile developers (TypeScript/JavaScript).** Their job is
putting an agent behind their own product surface: web dashboards, mobile apps,
internal tools. They need an npm package that owns the WebSocket protocol,
session management, streaming, and reconnection — so they ship agent features
without learning the binary protocol.

**Audience 3 — Polyglot developers / language-agnostic integrations.** Their job
is driving JiuwenSwarm from a language that cannot import Python — Go, Rust,
Java. They need a stable HTTP REST + WebSocket API, documented well enough to
write a client in any language — so JiuwenSwarm is reachable from anywhere,
not only from Python.

### WHEN

The existing codebase (`openjiuwen/core`, `openjiuwen/harness`) already
contains most of the logic needed for an SDK. The Python package (`openjiuwen`)
is installable today. The gap is: (1) the public API boundary is only partially
defined — `core/__init__.py` exports nothing, while `harness/__init__.py`
already exposes a lazy-loaded public API; (2) there is no TypeScript client
package; (3) there is no formally documented REST or WebSocket gateway.

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
| Session management | `Session` (deprecated), `create_agent_session`, `GlobalSessionController` | `Session.create()`, `.list()`, `.get()` |
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
`core/__init__.py` still exports nothing. `harness/__init__.py` already exports a
lazy-loaded public API (`DeepAgent`, `TaskLoopEventHandler`, `TaskLoopEventExecutor`,
`DeepAgentConfig`, `AudioModelConfig`, `VisionModelConfig`, `MultiRolloutConfig`,
`MultiRolloutExecutor`, `create_deep_agent`, `Workspace`). The SDK phase consolidates
these into the authoritative public export list. Internal modules are not re-exported.

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
