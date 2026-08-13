# Contributing

## Setup

```bash
uv sync
make install
make test          # run all tests
make check         # lint staged files
make type-check    # mypy on sdk/
```

---

## Adding a custom tool

A tool is a Python function decorated with `@tool`. The SDK infers the
JSON schema from type annotations automatically.

**1. Define the function:**

```python
# openjiuwen/sdk/tools.py  (or in your application code)
from openjiuwen.sdk import tool

@tool(name="word_count", description="Count words in a text.")
def word_count(text: str) -> int:
    return len(text.split())
```

**2. Pass it to the agent:**

```python
agent = await Agent.create("my-agent", model=cfg, tools=[word_count])
```

**3. Test it:**

```python
result = await word_count.ainvoke(text="hello world")
assert result == 2
```

**Rules for tool functions:**

- Sync or async — both are supported.
- Return type must be JSON-serialisable (str, int, float, bool, list, dict).
- Use `ToolParam` for enum-constrained arguments:

```python
from openjiuwen.sdk import tool, ToolParam

@tool(
    name="search",
    description="Search for content.",
    params=[ToolParam("mode", description="Search mode", enum=["fast", "deep"])],
)
async def search(query: str, mode: str = "fast") -> str:
    ...
```

---

## Adding a new workflow node type

Node types live in `openjiuwen/sdk/workflow.py`.

**1. Define the dataclass:**

```python
@dataclass(frozen=True)
class MyNode(WorkflowNode):
    my_param: str
    name: str = "my-node"
```

**2. Handle it in `_internal/workflow_bridge.py`:**

```python
def _node_to_component(node: WorkflowNode, model_cfg):
    if isinstance(node, MyNode):
        return MyRuntimeComponent(param=node.my_param)
    ...
```

**3. Export it from `__init__.py`:**

```python
from openjiuwen.sdk.workflow import MyNode
```

**4. Add tests in `tests/unit_tests/sdk/test_workflow.py`:**

```python
def test_my_node_added():
    wf = Workflow.create("test")
    wf.add_node(MyNode(my_param="value", name="n1"))
    assert "n1" in wf._nodes
```

---

## Adding a new backend adapter

Backend adapters (session stores, checkpointers) are registered by name
so application code can refer to them by string.

**1. Implement the interface:**

```python
from openjiuwen.sdk import SessionStore  # or CheckpointerBackend

class RedisSessionStore(SessionStore):
    def __init__(self, url: str): ...
    async def save(self, session_id: str, data: dict) -> None: ...
    async def load(self, session_id: str) -> dict | None: ...
    async def delete(self, session_id: str) -> None: ...
    async def list(self) -> list[str]: ...
```

**2. Register it:**

```python
from openjiuwen.sdk import register_store
register_store("redis", RedisSessionStore)
```

**3. Use it:**

```python
agent = await Agent.create(
    "my-agent",
    model=cfg,
    session_store="redis",
    session_store_kwargs={"url": "redis://localhost:6379"},
)
```

**4. Add unit tests** that patch the bridge and verify the store is
constructed and called with the correct arguments.

---

## Writing tests for SDK modules

All SDK unit tests follow the same pattern:

```python
# tests/unit_tests/sdk/test_my_module.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.fixture(autouse=True)
def patch_bridge(monkeypatch):
    monkeypatch.setattr(
        "openjiuwen.sdk._internal.my_bridge.my_function",
        AsyncMock(return_value="mocked"),
    )

@pytest.mark.asyncio
async def test_my_feature():
    from openjiuwen.sdk import MyClass
    obj = await MyClass.create("name")
    result = await obj.do_something("prompt")
    assert result.text == "mocked"
```

**Rules:**

- Patch bridge functions, not runtime classes.
- Use `AsyncMock` for `async def` functions, `MagicMock` for sync.
- One `autouse` fixture per test module that patches all bridges used
  by the façade under test.
- Test the happy path, error propagation (bridge raises, façade re-raises
  as the correct SDK error), and edge cases (empty inputs, None returns).
- Do not import from `openjiuwen.core` or `openjiuwen.harness` in unit
  tests — the bridge patch isolates them completely.

---

## Running targeted tests

```bash
make test TESTFLAGS="tests/unit_tests/sdk/test_agent.py"
make test TESTFLAGS="tests/unit_tests/sdk/test_workflow.py::test_run_returns_result"
```

---

## Before committing

```bash
make fix          # auto-format (black + isort + ruff --fix)
make check        # lint staged files
make type-check   # mypy openjiuwen/sdk/
make test TESTFLAGS="tests/unit_tests/sdk/"
```

Follow the git workflow in `.claude/rules/git-workflow.md`:
conventional commit messages, one logical change per PR, no `git add -A`.
