"""23_lsp_integration.py — live Language Server Protocol diagnostics for coding agents.

Corresponds to §23 of the usage examples.

Shows:
  - lsp.initialize_lsp() connecting to a language server (e.g., pyright)
  - lsp.get_lsp_status() to check readiness
  - lsp.get_lsp_tool() to expose LSP as an agent tool
  - Agent.create(tools=[lsp_tool]) integration
  - lsp.get_pending_lsp_diagnostics() for accumulated issues
  - lsp.shutdown_lsp() for clean teardown

Run:
    python examples/23_lsp_integration.py

Prerequisites:
    pyright must be installed: npm install -g pyright
"""

import asyncio
from openjiuwen.harness import lsp
from openjiuwen.harness.lsp import InitializeOptions


async def main():
    # Start the LSP server (e.g., pyright for Python)
    await lsp.initialize_lsp(
        options=InitializeOptions(
            server_command=["pyright-langserver", "--stdio"],
            root_uri="file:///workspace/project",
            language_id="python",
        )
    )

    # Check LSP readiness
    status = lsp.get_lsp_status()
    print(f"LSP ready: {status.ready}, server: {status.server_name}")

    # Expose the LSP tool to an agent — the agent can request diagnostics and
    # hover information autonomously during its task loop.
    lsp_tool = lsp.get_lsp_tool()

    from openjiuwen.sdk import Agent, ModelConfig
    agent = await Agent.create(
        "lsp-agent",
        model=ModelConfig.from_env(),
        tools=[lsp_tool],         # agent can call 'lsp_diagnostics', 'lsp_hover', etc.
    )

    result = await agent.run(
        "Fix all type errors in src/handlers.py. Use the LSP to verify each fix."
    )
    print(result.text)

    # Inspect accumulated diagnostics from this session
    diagnostics = lsp.get_pending_lsp_diagnostics(max_per_file=10, max_total=50)
    for file_diags in diagnostics:
        print(f"\n{file_diags.uri} — {len(file_diags.items)} remaining issues:")
        for item in file_diags.items:
            print(f"  line {item.range.start.line}: [{item.severity}] {item.message}")

    await lsp.shutdown_lsp()


if __name__ == "__main__":
    asyncio.run(main())
