"""13_checkpoint_restore.py — save and restore agent state across runs and processes.

Corresponds to §13 of the usage examples.

Shows:
  - agent.checkpoint() → opaque checkpoint ID
  - Agent.restore(checkpoint_id) to resume from saved state
  - checkpoint_every=N for automatic periodic checkpoints
  - checkpoint_store= for selecting a persistence backend

Run:
    python examples/13_checkpoint_restore.py
"""

import asyncio
from openjiuwen.sdk import Agent, ModelConfig


async def main():
    agent = await Agent.create("long-task", model=ModelConfig.from_env())

    # Start a multi-step task
    await agent.run("Step 1: outline a 10-chapter book on distributed systems.")

    # Save state — returns an opaque checkpoint ID
    checkpoint_id = await agent.checkpoint()
    print(f"Checkpoint saved: {checkpoint_id}")

    # --- some time later, or in a different process ---

    restored = await Agent.restore(checkpoint_id, model=ModelConfig.from_env())
    result = await restored.run("Step 2: write a 200-word summary of chapter 1.")
    print(result.text)


# ---------------------------------------------------------------------------
# Automatic checkpointing every N turns
# ---------------------------------------------------------------------------

async def auto_checkpoint_example():
    agent = await Agent.create(
        "auto-checkpoint",
        model=ModelConfig.from_env(),
        checkpoint_every=5,          # save after every 5 task-loop turns
        checkpoint_store="sqlite",   # or "postgres", "s3"
    )
    result = await agent.run("Write a detailed report on microservice architectures.")
    print(result.text)


if __name__ == "__main__":
    asyncio.run(main())
