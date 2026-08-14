"""hooks_lifecycle.py — observe every step of an agent run with Hooks.

Shows:
  - Decorator form: @hooks.token, @hooks.tool_call, etc.
  - Constructor form: Hooks(on_token=fn, ...)
  - Multiple callbacks per event
  - Passing Hooks to Agent.create()
  - Using Hooks to build a live token counter

Run:
    python examples/hooks_lifecycle.py
"""

import asyncio
import time

from openjiuwen.sdk import Agent, ModelConfig, tool
from openjiuwen.sdk.hooks import Hooks


# ---------------------------------------------------------------------------
# A simple tool so we get tool_call / tool_result events
# ---------------------------------------------------------------------------

@tool
def calculate(expression: str) -> float:
    """Evaluate a simple arithmetic expression and return the result."""
    return eval(expression, {"__builtins__": {}})  # noqa: S307 (demo only)


# ---------------------------------------------------------------------------
# Example 1 — decorator form
# ---------------------------------------------------------------------------

async def decorator_form_demo() -> None:
    print("=== Decorator form ===")

    hooks = Hooks()
    token_count = 0
    start_time = 0.0

    @hooks.start
    def on_start(prompt: str) -> None:
        nonlocal start_time
        start_time = time.monotonic()
        print(f"[start] prompt={prompt[:40]!r}…")

    @hooks.token
    def on_token(token: str) -> None:
        nonlocal token_count
        token_count += 1

    @hooks.tool_call
    def on_tool_call(name: str, args: dict) -> None:
        print(f"\n[tool_call] {name}({args})")

    @hooks.tool_result
    def on_tool_result(name: str, result: str) -> None:
        print(f"[tool_result] {name} → {result!r}")

    @hooks.done
    def on_done() -> None:
        elapsed = time.monotonic() - start_time
        print(f"\n[done] {token_count} tokens in {elapsed:.2f}s")

    @hooks.error
    def on_error(exc: Exception) -> None:
        print(f"[error] {exc}")

    agent = await Agent.create(
        "calculator",
        model=ModelConfig.from_env(),
        tools=[calculate],
        hooks=hooks,
    )

    result = await agent.run("What is 123 * 456 + 789?")
    print("Answer:", result.text)


# ---------------------------------------------------------------------------
# Example 2 — constructor form
# ---------------------------------------------------------------------------

async def constructor_form_demo() -> None:
    print("\n=== Constructor form ===")

    log: list[str] = []

    hooks = Hooks(
        on_token=lambda t: log.append(t),
        on_done=lambda: print(f"[done] collected {len(log)} tokens"),
    )

    # Add a second token callback on top of the first
    hooks.token(lambda t: print(".", end="", flush=True))

    agent = await Agent.create(
        "writer",
        model=ModelConfig.from_env(),
        hooks=hooks,
    )

    await agent.run("Write a one-line fortune cookie message.")
    full_response = "".join(log)
    print(f"\nFull text: {full_response!r}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

async def main() -> None:
    await decorator_form_demo()
    await constructor_form_demo()


if __name__ == "__main__":
    asyncio.run(main())
