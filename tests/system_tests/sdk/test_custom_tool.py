"""System tests for custom @tool integration — requires running JiuwenSwarm server.

Run with::

    pytest -m system tests/system_tests/sdk/test_custom_tool.py
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.system


def _runtime_available() -> bool:
    try:
        import openjiuwen.core  # noqa: F401

        return True
    except ImportError:
        return False


skip_no_runtime = pytest.mark.skipif(
    not _runtime_available(),
    reason="JiuwenSwarm runtime not installed",
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def add_tool():
    from openjiuwen.sdk import tool

    @tool
    def add(a: int, b: int) -> int:
        """Add two integers."""
        return a + b

    return add


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@skip_no_runtime
async def test_agent_uses_custom_tool(add_tool):
    """Agent should invoke the custom add() tool when asked."""
    from openjiuwen.sdk import Agent, ModelConfig

    model = ModelConfig.from_env()
    agent = await Agent.create(
        "tool-test",
        model=model,
        tools=[add_tool],
        system_prompt="You have an `add` tool. Use it when asked to add numbers.",
    )
    result = await agent.run("What is 7 + 8?")
    assert "15" in result.text, f"Expected 15 in response, got: {result.text!r}"


@pytest.mark.asyncio
@skip_no_runtime
async def test_custom_tool_schema_accessible(add_tool):
    """The @tool decorator should expose a schema attribute."""
    assert hasattr(add_tool, "schema") or hasattr(add_tool, "_schema")
    # The tool should be callable
    assert add_tool.fn(3, 4) == 7


@pytest.mark.asyncio
@skip_no_runtime
async def test_agent_with_multiple_tools():
    from openjiuwen.sdk import Agent, ModelConfig, tool

    @tool
    def multiply(a: int, b: int) -> int:
        """Multiply two integers."""
        return a * b

    @tool
    def greet(name: str) -> str:
        """Return a greeting for the given name."""
        return f"Hello, {name}!"

    model = ModelConfig.from_env()
    agent = await Agent.create(
        "multi-tool",
        model=model,
        tools=[multiply, greet],
    )
    result = await agent.run("What is 6 * 7?")
    assert "42" in result.text
