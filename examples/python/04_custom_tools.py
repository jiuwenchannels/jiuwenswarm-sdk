"""custom_tools.py — register Python functions as agent tools.

Shows:
  - @tool on a sync function (param inference from type annotations)
  - @tool on an async function
  - @tool with explicit name, description, and enum constraint
  - Calling tools directly via ainvoke() / invoke_sync()
  - Passing tools to Agent.create()

Run:
    python examples/custom_tools.py
"""

import asyncio
from datetime import datetime

import httpx

from openjiuwen.sdk import Agent, ModelConfig, ToolParam, tool


# ---------------------------------------------------------------------------
# Sync tool — parameters inferred from annotations
# ---------------------------------------------------------------------------

@tool
def word_count(text: str) -> int:
    """Count the number of words in the given text."""
    return len(text.split())


# ---------------------------------------------------------------------------
# Async tool — works identically to sync tools
# ---------------------------------------------------------------------------

@tool
async def fetch_url(url: str) -> str:
    """Fetch the content of a URL and return the first 500 characters."""
    async with httpx.AsyncClient() as client:
        response = await client.get(url, follow_redirects=True, timeout=10.0)
        return response.text[:500]


# ---------------------------------------------------------------------------
# Tool with explicit name, description, and enum constraint
# ---------------------------------------------------------------------------

@tool(
    name="current_time",
    description="Return the current date and time in the requested format.",
    params=[
        ToolParam(
            name="fmt",
            type="string",
            description="strftime format string.",
            required=False,
            enum=["%Y-%m-%d", "%H:%M:%S", "%Y-%m-%d %H:%M:%S"],
        )
    ],
)
def current_time(fmt: str = "%Y-%m-%d %H:%M:%S") -> str:
    return datetime.now().strftime(fmt)


# ---------------------------------------------------------------------------
# Calling a tool directly (without an agent)
# ---------------------------------------------------------------------------

async def direct_invocation_demo() -> None:
    # ainvoke always returns str
    count = await word_count.ainvoke(text="Hello beautiful world")
    print(f"word_count: {count!r}")

    now = await current_time.ainvoke(fmt="%Y-%m-%d")
    print(f"current_time: {now!r}")

    # Sync invocation
    count_sync = word_count.invoke_sync(text="one two three")
    print(f"word_count (sync): {count_sync!r}")

    # OpenAI function-call spec
    import json
    spec = word_count.to_tool_info()
    print("to_tool_info():", json.dumps(spec, indent=2))


# ---------------------------------------------------------------------------
# Passing tools to an agent
# ---------------------------------------------------------------------------

async def agent_with_tools_demo() -> None:
    agent = await Agent.create(
        "analyst",
        model=ModelConfig.from_env(),
        tools=[word_count, current_time],
    )

    result = await agent.run(
        "How many words are in 'The quick brown fox jumps over the lazy dog'? "
        "Also tell me today's date."
    )
    print("\nAgent response:", result.text)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    print("=== Direct tool invocation ===")
    await direct_invocation_demo()

    print("\n=== Agent with tools ===")
    await agent_with_tools_demo()


if __name__ == "__main__":
    asyncio.run(main())
