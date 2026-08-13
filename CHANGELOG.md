# Changelog

All notable changes to `openjiuwen-sdk` are documented here.
Versions follow [Semantic Versioning](https://semver.org/).

---

## [Unreleased]

### Added
- `docs/overview.md` — project description and current feature inventory
- `docs/architecture.md` — bridge/façade pattern, module layout, dependency rules
- `docs/contributing.md` — how to add tools, workflow nodes, backends, and tests
- `docs/configuration.md` — complete env var and config-class reference
- `examples/python/` — all 29+4 Python SDK examples (§01–§29, plus `05b`, `16b`, `17b`)
- `examples/typescript/` — 6 TypeScript SDK examples (§01–§06)
- `examples/rest/` — 9 REST / cURL shell examples (§01–§09)

---

## [0.3.0] — 2024-08-xx

### Added
- `docs/api-reference.md` — full API reference for all public classes and methods
- `docs/roadmap.md` — upcoming features and phase plan

---

## [0.2.0] — 2024-08-xx

### Added
- **Workflow DAG façade** (`openjiuwen.sdk.workflow`)
  - `Workflow.create()`, `add_node()`, `connect()`, `branch()`
  - `workflow.run()`, `workflow.stream()`, `workflow.draw()`
  - Node types: `LLMNode`, `ToolNode`, `ConditionNode`
  - `WorkflowResult` frozen dataclass
  - `WorkflowError` in error hierarchy
  - Internal bridge: `sdk/_internal/workflow_bridge.py`
  - 30 unit tests

- **A2A remote agent client** (`openjiuwen.sdk.a2a`)
  - `RemoteAgent(url, agent_id)` with `run()`, `stream()`, `cancel()`, `close()`
  - Context manager support
  - `A2AResult` frozen dataclass
  - `A2AError` in error hierarchy
  - Internal bridge: patchable `_create_a2a_client`, `_a2a_invoke`, `_a2a_stream`
  - 22 unit tests

- **Lifecycle hooks** (`openjiuwen.sdk.hooks`)
  - `Hooks` container with six slots: `on_token`, `on_tool_call`, `on_tool_result`, `on_done`, `on_error`, `on_start`
  - Decorator form (`@hooks.token`, `@hooks.tool_call`, …)
  - Constructor form (`Hooks(on_token=fn, …)`)
  - `hooks.wire(emitter)` — binds all callbacks into an `EventEmitter`
  - `Agent.create(hooks=hooks)` — wired automatically after agent init
  - 25 unit tests

### Changed
- `openjiuwen/sdk/__init__.py` — added exports for all new public symbols

---

## [0.1.0] — 2024-08-xx

Initial release. Covers Phase 0 (Python public API stabilisation)
and Phase 1 (core SDK façades).

### Added
- **Error hierarchy** (`openjiuwen.sdk.errors`)
  - `SdkError` base class
  - `ConnectionError`, `AuthError`, `SessionNotFoundError`, `ToolError`,
    `TimeoutError`, `ProtocolError`, `ServerError`, `ConfigError`

- **Configuration** (`openjiuwen.sdk.config`)
  - `ModelConfig` — frozen dataclass for in-process LLM config
  - `RemoteConfig` — frozen dataclass for WebSocket remote config
  - `SdkConfig` — combined config with `from_env()` classmethod
  - All fields documented; env var fallbacks tested

- **EventEmitter** (`openjiuwen.sdk.events`)
  - `on` / `off` / `off_all`
  - Sync `emit` (schedules async callbacks on loop)
  - Async `emit_async` (awaits all callbacks in order)

- **Agent façade** (`openjiuwen.sdk.agent`)
  - `Agent.create(name, model, tools, hooks)` — in-process mode
  - `Agent.connect(name, config)` — remote WebSocket mode
  - `agent.run(prompt, session_id)` → `AgentResult`
  - `agent.stream(prompt, session_id)` → `AsyncIterator[str]`
  - `agent.on(event, callback)` / `agent.off(event, callback)`
  - `agent.checkpoint()` → `str` (opaque checkpoint ID)
  - `Agent.restore(checkpoint_id)` → `Agent`
  - `agent.run_sync(prompt)` — sync wrapper

- **Session façade** (`openjiuwen.sdk.session`)
  - `Session.create(title, mode)`, `Session.list()`, `Session.get(id)`, `session.delete()`
  - `session.history()` → `list[Message]`
  - `SessionInfo`, `Message` frozen dataclasses

- **Tool decorator** (`openjiuwen.sdk.tools`)
  - `@tool(name, description, params)` — wraps sync and async functions
  - Type annotation inference for all JSON-schema types
  - Optional parameters via default values
  - Enum constraints via `ToolParam`
  - `tool.to_tool_info()` — OpenAI-compatible function spec
  - `tool.ainvoke(**kwargs)`, `tool.invoke_sync(**kwargs)`

- **Team façade** (`openjiuwen.sdk.team`)
  - `Team.create(agents)` → `Team`
  - `team.spawn(prompt)` → `TeamResult`
  - `team.send(message, to=agent_name)`
  - `TeamResult`, `TeamStatus` frozen dataclasses

- **Internal bridges** (`openjiuwen/sdk/_internal/`)
  - `runner_bridge.py`, `session_bridge.py`, `team_bridge.py`, `sync_wrapper.py`
  - All use module-level wrapper functions for monkeypatching in tests

- **Public namespace** (`openjiuwen/sdk/__init__.py`)
  - All public symbols re-exported; sub-module imports are not part of the stable API

- **Packaging** (`pyproject.toml`)
  - `openjiuwen-sdk` distribution; `[runtime]` extra for in-process deps
  - `pip install openjiuwen-sdk` / `pip install openjiuwen-sdk[runtime]`

- **Unit tests** — 79 tests across all façade modules, all passing
