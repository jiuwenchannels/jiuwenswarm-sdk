"""22_security_rails.py — fine-grained tool permission enforcement.

Corresponds to §22 of the usage examples.

Shows:
  - PermissionsSection with default_level and per-tool overrides
  - PermissionLevel.ALLOW / ASK / DENY
  - trusted_directories restricting file operations
  - Agent.create(permission_engine=...) integration
  - CLIApprovalHost for human-in-the-loop tool approval
  - engine.update_config() and engine.update_trusted_dirs() at runtime

Run:
    python examples/22_security_rails.py
"""

import asyncio
from openjiuwen.sdk import Agent, ModelConfig
from openjiuwen.harness.security import (
    PermissionEngine,
    PermissionsSection,
    PermissionLevel,
)


# Define a permission policy: allow read-only tools, require approval for writes,
# block destructive file operations entirely.
policy = PermissionsSection(
    default_level=PermissionLevel.ALLOW,
    tool_overrides={
        "shell":          PermissionLevel.ASK,       # prompt before any shell command
        "file_write":     PermissionLevel.ASK,
        "file_delete":    PermissionLevel.DENY,      # never allowed
        "process_kill":   PermissionLevel.DENY,
    },
    trusted_directories=["/workspace/project"],      # restrict file ops to this tree
)

engine = PermissionEngine(config=policy)


async def main():
    agent = await Agent.create(
        "guarded-agent",
        model=ModelConfig.from_env(),
        permission_engine=engine,
    )

    # The agent can read freely, must ask before writing, and cannot delete files.
    result = await agent.run("Refactor src/utils.py to use pathlib.")
    print(result.text)


# ---------------------------------------------------------------------------
# Custom approval callback — human-in-the-loop for permission prompts
# ---------------------------------------------------------------------------

from openjiuwen.harness.security import ToolPermissionHost, PermissionConfirmationRequest


class CLIApprovalHost(ToolPermissionHost):
    async def request_confirmation(
        self, req: PermissionConfirmationRequest
    ) -> bool:
        answer = input(f"\n[SECURITY] Allow tool '{req.tool_name}'? (y/n): ")
        return answer.strip().lower() == "y"


def interactive_engine_example():
    """Build an engine that prompts the user before each sensitive tool call."""
    return PermissionEngine(config=policy, host=CLIApprovalHost())


# ---------------------------------------------------------------------------
# Runtime policy update
# ---------------------------------------------------------------------------

def update_policy_example():
    engine.update_config(PermissionsSection(default_level=PermissionLevel.ALLOW))
    engine.update_trusted_dirs(["/workspace/project", "/workspace/data"])


if __name__ == "__main__":
    asyncio.run(main())
