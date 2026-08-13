# Architecture

## Design philosophy

The SDK is a thin **façade** over the existing `openjiuwen.core` and
`openjiuwen.harness` runtimes. It owns the public API contract; the
runtimes own the execution logic. The two layers must not bleed into
each other: no internal runtime type should appear in a public SDK
method signature.

---

## Layer diagram

```
┌─────────────────────────────────────────────────────────┐
│                   Application code                       │
│         from openjiuwen.sdk import Agent, tool          │
└────────────────────────┬────────────────────────────────┘
                         │ public API
┌────────────────────────▼────────────────────────────────┐
│                  openjiuwen/sdk/                         │
│  agent.py  session.py  tools.py  workflow.py            │
│  a2a.py    hooks.py    team.py   events.py              │
│  config.py  errors.py                                   │
└────────────────────────┬────────────────────────────────┘
                         │ internal bridge calls
┌────────────────────────▼────────────────────────────────┐
│              openjiuwen/sdk/_internal/                   │
│  runner_bridge.py     session_bridge.py                 │
│  team_bridge.py       workflow_bridge.py                │
│  sync_wrapper.py                                        │
└────────────────────────┬────────────────────────────────┘
                         │ runtime imports
┌────────────────────────▼────────────────────────────────┐
│   openjiuwen.core  /  openjiuwen.harness                │
│   Runner, SessionManager, DeepAgent, …                  │
└─────────────────────────────────────────────────────────┘
```

---

## The bridge pattern

Each `_internal/` module follows the same structure:

```python
# openjiuwen/sdk/_internal/runner_bridge.py

from openjiuwen.core import Runner  # runtime import at top level

# Module-level wrapper functions (not class methods).
# Tests replace these by patching the module attribute.

def make_agent_card(name: str, tools, model_cfg) -> "AgentCard":
    ...

async def run_agent(card, prompt: str, session_id: str | None) -> str:
    runner = Runner.get()
    ...

async def stream_agent(card, prompt: str, session_id: str | None):
    ...
```

The façade module imports the bridge at module level and calls its
functions by name:

```python
# openjiuwen/sdk/agent.py
from openjiuwen.sdk._internal import runner_bridge as _rb

class Agent:
    async def run(self, prompt: str) -> AgentResult:
        raw = await _rb.run_agent(self._card, prompt, self._session_id)
        return AgentResult(text=raw)
```

**Why module-level functions (not class methods)?**
Tests can replace them with a single `monkeypatch.setattr`:

```python
monkeypatch.setattr("openjiuwen.sdk._internal.runner_bridge.run_agent",
                    AsyncMock(return_value="mocked response"))
```

No need to mock class instantiation or `Runner.get()`.

---

## Bridge modules

| Module | Wraps | Key functions |
|--------|-------|---------------|
| `runner_bridge.py` | `openjiuwen.core.Runner` | `make_agent_card`, `run_agent`, `stream_agent`, `checkpoint_agent`, `restore_agent` |
| `session_bridge.py` | `openjiuwen.core.SessionManager` | `create_session`, `list_sessions`, `get_session`, `delete_session`, `get_history` |
| `team_bridge.py` | `openjiuwen.harness` team runtime | `make_team_card`, `create_team_session`, `spawn_team`, `send_team_message`, `team_status` |
| `workflow_bridge.py` | workflow runtime | `make_workflow_card`, `build_runtime_workflow`, `run_workflow`, `stream_workflow` |
| `sync_wrapper.py` | Python event loop | `run_sync(coro)` — runs a coroutine in a new loop; raises `RuntimeError` if called from within a running loop |

---

## Public API contract

**Rule:** Every type that appears in a public method signature must be
defined in `openjiuwen/sdk/` (not in `openjiuwen.core` or
`openjiuwen.harness`).

Good:
```python
async def run(self, prompt: str) -> AgentResult: ...   # AgentResult is in sdk/agent.py
```

Bad:
```python
async def run(self, prompt: str) -> CoreResult: ...    # CoreResult is a runtime type
```

When a runtime returns an internal type, the bridge unwraps it to a
plain dict or string and the façade wraps it in the appropriate SDK
dataclass.

---

## Card / Config split

This mirrors the core runtime convention:

- **Cards** (`AgentCard`, `WorkflowCard`, `TeamCard`) define identity and
  metadata — name, tool list, model reference. They are frozen dataclasses.
  Created once, passed to the runtime, never mutated.
- **Configs** (`ModelConfig`, `RemoteConfig`) are runtime-knobs — API key,
  temperature, timeout. Also frozen dataclasses. Passed to `Agent.create()`
  and forwarded to the bridge.

The SDK creates cards internally in the bridge; application code only
ever sees configs.

---

## EventEmitter and Hooks

`EventEmitter` (`sdk/events.py`) is a standalone typed pub/sub:

```
event name → list[callback]
```

`emit(name, *args)` schedules each async callback on the running event
loop using `asyncio.ensure_future`. `emit_async` awaits them in order.

`Hooks` (`sdk/hooks.py`) is a frozen-style container that holds lists of
callbacks for six named lifecycle events. `hooks.wire(emitter)` registers
all callbacks into an `EventEmitter`. The `Agent.create(hooks=hooks)` path
calls `hooks.wire(agent)` after the agent is initialised.

---

## Sync wrapper

`run_sync(coro)` in `sync_wrapper.py` creates a new event loop with
`asyncio.new_event_loop()`, runs the coroutine to completion, and
closes the loop. It raises `RuntimeError` when called from within a
running loop (i.e., inside an `async def`), because nesting loops is
not supported in CPython. Users should use `await agent.run()` in async
contexts.

---

## Adding a new façade module

1. Create `openjiuwen/sdk/_internal/my_bridge.py` with module-level
   wrapper functions.
2. Create `openjiuwen/sdk/my_module.py` with the public class. Import
   the bridge as `from openjiuwen.sdk._internal import my_bridge as _mb`.
3. Export the public class from `openjiuwen/sdk/__init__.py`.
4. Write unit tests in `tests/unit_tests/sdk/test_my_module.py` that
   patch `_mb.function_name` with `AsyncMock` / `MagicMock`.
5. Add an example to `examples/python/`.

---

## Testing strategy

**Unit tests** (`tests/unit_tests/sdk/`) are fully deterministic:

- All bridge functions are patched — no live runtime, no network.
- Each test file patches the bridge module used by the façade under test.
- Tests use `pytest-asyncio` with `asyncio_mode = "auto"`.

**System tests** (`tests/system_tests/sdk/`) run against a live local
server:

- Marked `@pytest.mark.system`.
- Skipped in CI by default (no credentials).
- Required before any major version release.

---

## Dependency rules

- `openjiuwen/sdk/` may import from `openjiuwen/sdk/_internal/`.
- `openjiuwen/sdk/_internal/` may import from `openjiuwen.core` and
  `openjiuwen.harness`.
- `openjiuwen/sdk/` must NOT import directly from `openjiuwen.core` or
  `openjiuwen.harness` (this is the bridge's job).
- Circular imports between `sdk/` modules are forbidden; use
  `TYPE_CHECKING` guards for type-only references.
