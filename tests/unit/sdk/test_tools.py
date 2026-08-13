"""Tests for openjiuwen.sdk.core.tools — @tool decorator and SdkTool."""

from __future__ import annotations

import asyncio

import pytest

from openjiuwen.sdk.core.errors import ToolError
from openjiuwen.sdk.core.tools import SdkTool, ToolParam, tool


class TestToolDecorator:
    def test_bare_decorator_sync(self):
        @tool
        def add(a: int, b: int) -> int:
            """Add two integers."""
            return a + b

        assert isinstance(add, SdkTool)
        assert add.name == "add"
        assert add.description == "Add two integers."

    def test_bare_decorator_async(self):
        @tool
        async def fetch(url: str) -> str:
            """Fetch a URL."""
            return url

        assert "Fetch" in fetch.description

    def test_with_explicit_name_and_description(self):
        @tool(name="my_tool", description="Does something useful.")
        def fn(x: str) -> str:
            return x

        assert fn.name == "my_tool"
        assert fn.description == "Does something useful."

    def test_param_inference(self):
        @tool
        def fn(name: str, count: int, active: bool) -> str:
            return ""

        params = {p.name: p for p in fn.params}
        assert params["name"].type == "string"
        assert params["count"].type == "integer"
        assert params["active"].type == "boolean"

    def test_all_params_required(self):
        @tool
        def fn(a: str, b: str) -> str:
            return ""

        assert all(p.required for p in fn.params)

    def test_optional_param_not_required(self):
        @tool
        def fn(required: str, optional: str = "default") -> str:
            return ""

        params = {p.name: p for p in fn.params}
        assert params["required"].required
        assert not params["optional"].required

    def test_to_tool_info_shape(self):
        @tool(name="greet", description="Greet a person.")
        def fn(name: str) -> str:
            return f"Hello, {name}"

        info = fn.to_tool_info()
        assert info["type"] == "function"
        f = info["function"]
        assert f["name"] == "greet"
        assert f["description"] == "Greet a person."
        assert "name" in f["parameters"]["properties"]
        assert "name" in f["parameters"]["required"]

    def test_to_tool_info_no_params(self):
        @tool(name="ping", description="Ping.")
        def fn() -> str:
            return "pong"

        info = fn.to_tool_info()
        assert info["function"]["parameters"]["required"] == []

    def test_custom_params(self):
        params = [
            ToolParam(name="mode", type="string", description="Mode.", required=True,
                      enum=["fast", "slow"]),
        ]

        @tool(name="run", params=params)
        def fn(mode: str) -> str:
            return mode

        info = fn.to_tool_info()
        prop = info["function"]["parameters"]["properties"]["mode"]
        assert prop["enum"] == ["fast", "slow"]


class TestSdkToolInvoke:
    @pytest.mark.asyncio
    async def test_ainvoke_sync_fn(self):
        @tool
        def multiply(a: int, b: int) -> int:
            """Multiply."""
            return a * b

        result = await multiply.ainvoke(a=3, b=4)
        assert result == "12"

    @pytest.mark.asyncio
    async def test_ainvoke_async_fn(self):
        @tool
        async def echo(msg: str) -> str:
            """Echo."""
            return msg

        result = await echo.ainvoke(msg="hello")
        assert result == "hello"

    @pytest.mark.asyncio
    async def test_ainvoke_returns_str(self):
        @tool
        def stringify(n: int) -> int:
            return n

        result = await stringify.ainvoke(n=42)
        assert isinstance(result, str)
        assert result == "42"

    @pytest.mark.asyncio
    async def test_ainvoke_raises_tool_error_on_exception(self):
        @tool
        def broken() -> str:
            raise ValueError("bad input")

        with pytest.raises(ToolError, match="broken"):
            await broken.ainvoke()

    def test_invoke_sync(self):
        @tool
        def add(a: int, b: int) -> int:
            return a + b

        result = add.invoke_sync(a=10, b=5)
        assert result == "15"
