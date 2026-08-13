# Contributing

## Repository layout

```
openjiuwen/sdk/          Python SDK façades and bridges
openjiuwen/gateway/      HTTP + WebSocket gateway (FastAPI)
openjiuwen/agent_teams/  Team runtime and MCP server
packages/sdk/            TypeScript SDK (@jiuwenswarm/sdk)
tests/unit_tests/sdk/    Fast deterministic Python SDK tests
tests/unit_tests/gateway/  Fast gateway route tests
tests/system_tests/      E2E tests against a live local server
examples/python/         §01–§29 Python runnable examples
examples/typescript/     §01–§06 TypeScript examples
examples/rest/           §01–§09 REST/cURL shell scripts
docs/                    All documentation
```

## Setup

```bash
uv sync
make install
make test          # all Python tests
make check         # lint staged files
make type-check    # mypy on sdk/ and gateway/
```

TypeScript SDK:
```bash
cd packages/sdk
npm install
npm test           # vitest
npm run build      # tsup → dist/
npm run docs       # TypeDoc → packages/sdk/docs/
```

---

## Python SDK — adding a feature

### Adding a custom tool

```python
from openjiuwen.sdk import tool, ToolParam

@tool(name="my_tool", description="Does something useful.")
async def my_tool(query: str, mode: str = "fast") -> str:
    ...
```

Rules:
- Sync or async — both supported.
- Return type must be JSON-serialisable.
- Use `ToolParam` for enum-constrained arguments.
- Test with `tool.ainvoke(**kwargs)`.

### Adding a new workflow node type

1. Define a frozen dataclass extending `WorkflowNode` in `sdk/workflow.py`.
2. Handle it in `_internal/workflow_bridge.py` inside `_node_to_component`.
3. Export from `sdk/__init__.py`.
4. Add tests in `tests/unit_tests/sdk/test_workflow.py`.

### Adding a new backend adapter

1. Implement the `SessionStore` or `CheckpointerBackend` protocol from
   `sdk/stores.py`.
2. Place it in `sdk/contrib/<name>.py`.
3. Document registration in `docs/configuration.md`.
4. Add unit tests.

### Adding a new façade module

1. Create `sdk/_internal/my_bridge.py` with module-level wrapper functions.
2. Create `sdk/my_module.py`; import the bridge as `import ... as _mb`.
3. Export public symbols from `sdk/__init__.py`.
4. Write unit tests in `tests/unit_tests/sdk/test_my_module.py`.
5. Add an example to `examples/python/`.

---

## Python SDK — writing tests

All SDK unit tests follow this pattern:

```python
# tests/unit_tests/sdk/test_my_module.py
import pytest
from unittest.mock import AsyncMock, MagicMock

@pytest.fixture(autouse=True)
def patch_bridge(monkeypatch):
    monkeypatch.setattr(
        "openjiuwen.sdk._internal.my_bridge.my_function",
        AsyncMock(return_value="mocked"),
    )

@pytest.mark.asyncio
async def test_my_feature():
    from openjiuwen.sdk import MyClass
    result = await MyClass.create("name").do_something("prompt")
    assert result.text == "mocked"
```

Rules:
- Patch bridge module attributes, not runtime classes.
- Use `AsyncMock` for `async def`, `MagicMock` for sync.
- Test: happy path, error propagation (bridge raises → correct SDK error),
  edge cases (empty inputs, None).
- Never import from `openjiuwen.core` or `.harness` in unit tests.

System tests live in `tests/system_tests/sdk/` and are marked
`@pytest.mark.system`. They require a running local server and are not
run in CI by default.

---

## Gateway — adding a REST route

1. Add the route handler in the appropriate `openjiuwen/gateway/rest/` file.
2. Mount it in `openjiuwen/gateway/app.py` via `build_gateway_app`.
3. Write unit tests in `tests/unit_tests/gateway/` using
   `httpx.AsyncClient` with the FastAPI test app.
4. Add a cURL example to `examples/rest/`.

All routes must:
- Be prefixed `/v1/`.
- Return typed Pydantic response models.
- Pass through the auth middleware (handled globally).
- Include a success case and a 4xx error case in unit tests.

---

## TypeScript SDK — adding a feature

1. Add types to `packages/sdk/src/protocol/types.ts` if new envelope
   shapes are involved.
2. Implement the feature in the appropriate `src/` module.
3. Export from `src/index.ts`.
4. Write vitest tests in `packages/sdk/tests/`.
5. Update `packages/sdk/README.md` if the public API changes.
6. Run `npm run build` to verify the dual CJS+ESM output.
7. Run `npm run docs` to verify TypeDoc generates without errors.

---

## Running targeted tests

```bash
# Python — single file
make test TESTFLAGS="tests/unit_tests/sdk/test_agent.py"

# Python — single test
make test TESTFLAGS="tests/unit_tests/sdk/test_workflow.py::test_run_returns_result"

# Gateway tests
make test TESTFLAGS="tests/unit_tests/gateway/"

# TypeScript
cd packages/sdk && npm test
```

---

## Pre-commit checklist

```bash
make fix           # black + isort + ruff --fix
make check         # lint staged files
make type-check    # mypy openjiuwen/sdk/ openjiuwen/gateway/
make test TESTFLAGS="tests/unit_tests/"
```

Commit message format (conventional commits):
```
feat(sdk): add AgenticRetriever multi-round query rewriting
fix(gateway): return 404 when session not found
docs(architecture): update bridge diagram
test(sdk): add workflow sub-workflow composition tests
```

See `.claude/rules/git-workflow.md` for the full workflow.

---

## Public API contract

A change is **breaking** if it removes or renames a symbol exported from
`openjiuwen/sdk/__init__.py` or `packages/sdk/src/index.ts`. Breaking
changes require a major version bump. Adding new exports is never breaking.

The gateway REST routes at `/v1/` are stable. Breaking changes to any
route require a new `/v2/` prefix and a deprecation period for `/v1/`.

The WebSocket envelope protocol is frozen at version `"1"`. New fields
may be added to any envelope. Fields may not be removed or renamed without
a version bump to `"2"` in `ack.protocol_version`.
