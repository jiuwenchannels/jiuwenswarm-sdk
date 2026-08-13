"""06_long_term_memory.py — persistent memory scoped to users or sessions.

Corresponds to §6 of the usage examples.

Shows:
  - MemoryScope.USER for per-user persistence
  - agent.memory.add() to store explicit facts
  - agent.memory.search() to retrieve relevant memories
  - Automatic memory injection into agent context

Run:
    python examples/06_long_term_memory.py
"""

import asyncio
from openjiuwen.sdk import Agent, ModelConfig
from openjiuwen.sdk.memory import MemoryScope


async def main():
    agent = await Agent.create(
        "memory-agent",
        model=ModelConfig.from_env(),
        memory_scope=MemoryScope.USER,   # persists per user_id
        user_id="user_42",
    )

    # Store a fact explicitly
    await agent.memory.add("The user prefers responses in bullet points.")

    # Retrieve relevant memories before a prompt
    memories = await agent.memory.search("user preferences")
    for m in memories:
        print(f"  [{m.score:.2f}] {m.text}")

    # Agent automatically injects relevant memories into context
    result = await agent.run("Explain the Python GIL.")
    print(result.text)  # Response will be in bullet points


if __name__ == "__main__":
    asyncio.run(main())
