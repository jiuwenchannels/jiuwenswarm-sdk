"""16_task_loop_hooks.py — observe and intercept every step of the agent task loop.

Corresponds to §16 of the usage examples.

Shows:
  - TaskLoopEventHandler subclass with all lifecycle methods
  - on_turn_start, on_tool_call, on_tool_result, on_llm_call, on_done, on_error
  - Agent.create(event_handler=...) integration
  - ToolGuard: blocking a tool call by returning early with a custom response

Run:
    python examples/16_task_loop_hooks.py
"""

import asyncio
from openjiuwen.sdk import Agent, ModelConfig
from openjiuwen.sdk.hooks import TaskLoopEventHandler


class AuditLogger(TaskLoopEventHandler):
    """Logs every tool call to stdout for auditing."""

    async def on_turn_start(self, turn: int) -> None:
        print(f"[turn {turn}] starting")

    async def on_tool_call(self, name: str, args: dict) -> None:
        print(f"[tool] {name}({args})")

    async def on_tool_result(self, name: str, result: str) -> None:
        print(f"[tool] {name} → {result[:120]}")

    async def on_llm_call(self, messages: list) -> None:
        print(f"[llm] {len(messages)} messages in context")

    async def on_done(self, result) -> None:
        print(f"[done] {len(result.text)} chars output")

    async def on_error(self, error: Exception) -> None:
        print(f"[error] {type(error).__name__}: {error}")


class ToolGuard(TaskLoopEventHandler):
    """Blocks destructive shell commands before they execute."""

    async def on_tool_call(self, name: str, args: dict) -> "str | None":
        if name == "shell" and "rm" in args.get("command", ""):
            return "Error: destructive shell commands are not allowed."
        return None   # None means: proceed normally


async def main():
    agent = await Agent.create(
        "hooked-agent",
        model=ModelConfig.from_env(),
        event_handler=AuditLogger(),
    )
    await agent.run("List the files in the current directory and count them.")


if __name__ == "__main__":
    asyncio.run(main())
