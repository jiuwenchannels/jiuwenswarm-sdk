"""12_workspace.py — bound, file-system-aware coding agent.

Corresponds to §12 of the usage examples.

Shows:
  - Workspace(root=...) binding the agent to a directory
  - Agent.create(workspace=...) integration
  - workspace.diff() to inspect what changed
  - workspace.modified_files listing
  - Sandbox mode with an isolated container

Run:
    python examples/12_workspace.py
"""

import asyncio
from openjiuwen.sdk import Agent, ModelConfig
from openjiuwen.sdk.workspace import Workspace


async def main():
    # Point the workspace at an existing project
    workspace = Workspace(root="/path/to/my-project")

    agent = await Agent.create(
        "code-agent",
        workspace=workspace,
        model=ModelConfig.from_env(),
    )

    # Agent reads, edits, and runs code inside the workspace
    result = await agent.run(
        "Find all TODO comments in the Python files and create a TASKS.md "
        "that lists each one with its file and line number."
    )
    print(result.text)

    # Inspect what the agent changed
    diff = await workspace.diff()
    print(diff)

    # Workspace tracks created/modified files
    for path in workspace.modified_files:
        print(f"  modified: {path}")


# ---------------------------------------------------------------------------
# Sandbox mode — agent runs in an isolated container
# ---------------------------------------------------------------------------

def sandbox_workspace_example():
    workspace = Workspace(
        root="/path/to/my-project",
        sandbox=True,           # run shell commands in a container
        sandbox_image="python:3.11-slim",
    )
    return workspace


if __name__ == "__main__":
    asyncio.run(main())
