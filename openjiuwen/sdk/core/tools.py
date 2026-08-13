"""SDK tool registration helpers.

The :func:`tool` decorator wraps a Python function and produces an
:class:`SdkTool` that the :class:`~openjiuwen.sdk.core.agent.Agent` can use.

Usage::

    from openjiuwen.sdk import tool

    @tool(name="fetch_url", description="Fetch the text content of a URL.")
    async def fetch_url(url: str) -> str:
        ...

    agent = await Agent.create("my-agent", tools=[fetch_url], ...)
"""

from __future__ import annotations

import asyncio
import inspect
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Union, overload

from openjiuwen.sdk.core.errors import ToolError


# ---------------------------------------------------------------------------
# Public data types
# ---------------------------------------------------------------------------


@dataclass
class ToolParam:
    """Describes a single parameter of a tool."""

    name: str
    type: str = "string"
    description: str = ""
    required: bool = True
    enum: list[str] | None = None


@dataclass
class SdkTool:
    """A callable tool registered with the SDK.

    Attributes:
        name:        Tool name as seen by the LLM.
        description: One-sentence description used in the LLM system prompt.
        params:      Parameter definitions derived from the function signature.
        fn:          The underlying async (or sync) function.
    """

    name: str
    description: str
    params: list[ToolParam]
    fn: Callable

    # ------------------------------------------------------------------
    # Invocation
    # ------------------------------------------------------------------

    async def ainvoke(self, **kwargs: Any) -> str:
        """Invoke the tool asynchronously, returning a string result."""
        try:
            if inspect.iscoroutinefunction(self.fn):
                result = await self.fn(**kwargs)
            else:
                result = await asyncio.to_thread(self.fn, **kwargs)
        except Exception as exc:
            raise ToolError(f"Tool '{self.name}' raised {type(exc).__name__}: {exc}") from exc

        if isinstance(result, str):
            return result
        return str(result)

    def invoke_sync(self, **kwargs: Any) -> str:
        """Invoke the tool synchronously (blocks the event loop — use only outside async context)."""
        return asyncio.run(self.ainvoke(**kwargs))

    # ------------------------------------------------------------------
    # Serialisation helpers (for passing to the runtime)
    # ------------------------------------------------------------------

    def to_tool_info(self) -> dict[str, Any]:
        """Return an OpenAI-style tool definition dict."""
        properties: dict[str, Any] = {}
        required: list[str] = []
        for p in self.params:
            prop: dict[str, Any] = {"type": p.type, "description": p.description}
            if p.enum:
                prop["enum"] = p.enum
            properties[p.name] = prop
            if p.required:
                required.append(p.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


# ---------------------------------------------------------------------------
# Parameter introspection
# ---------------------------------------------------------------------------

_PY_TYPE_MAP: dict[str, str] = {
    "str": "string",
    "int": "integer",
    "float": "number",
    "bool": "boolean",
    "list": "array",
    "dict": "object",
}


def _infer_params(fn: Callable) -> list[ToolParam]:
    sig = inspect.signature(fn)
    hints = {}
    try:
        hints = fn.__annotations__
    except AttributeError:
        pass

    params: list[ToolParam] = []
    for pname, param in sig.parameters.items():
        if pname in ("self", "cls"):
            continue
        raw_type = hints.get(pname, "str")
        # unwrap Optional[X] → X
        origin = getattr(raw_type, "__origin__", None)
        if origin is Union:
            args = [a for a in raw_type.__args__ if a is not type(None)]
            raw_type = args[0] if args else str
        type_name = getattr(raw_type, "__name__", str(raw_type))
        json_type = _PY_TYPE_MAP.get(type_name, "string")
        required = param.default is inspect.Parameter.empty
        params.append(ToolParam(name=pname, type=json_type, required=required))
    return params


# ---------------------------------------------------------------------------
# @tool decorator
# ---------------------------------------------------------------------------

try:
    from typing import Union  # noqa: F401 (already imported above)
except ImportError:
    pass


@overload
def tool(fn: Callable) -> SdkTool: ...


@overload
def tool(
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    params: Optional[list[ToolParam]] = None,
) -> Callable[[Callable], SdkTool]: ...


def tool(
    fn: Optional[Callable] = None,
    *,
    name: Optional[str] = None,
    description: Optional[str] = None,
    params: Optional[list[ToolParam]] = None,
) -> Union[SdkTool, Callable[[Callable], SdkTool]]:
    """Decorator that turns a function into an :class:`SdkTool`.

    Can be used with or without arguments::

        @tool
        async def simple(x: str) -> str: ...

        @tool(name="my_tool", description="Does something.")
        async def explicit(x: str) -> str: ...
    """

    def _wrap(func: Callable) -> SdkTool:
        tool_name = name or func.__name__
        tool_desc = description or (inspect.getdoc(func) or "").split("\n")[0]
        tool_params = params if params is not None else _infer_params(func)
        return SdkTool(name=tool_name, description=tool_desc, params=tool_params, fn=func)

    if fn is not None:
        # Used as bare @tool
        return _wrap(fn)
    # Used as @tool(...)
    return _wrap
