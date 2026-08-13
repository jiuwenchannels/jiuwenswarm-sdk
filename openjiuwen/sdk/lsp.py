"""SDK LSP Integration façade — Language Server Protocol diagnostics for coding agents.

Attaches a Language Server (e.g. pyright, typescript-language-server) to an
agent so it can request type-check diagnostics and hover information during
its task loop.

Quick start::

    from openjiuwen.sdk.lsp import LSPIntegration

    lsp = LSPIntegration.attach(
        agent,
        server_cmd=["pyright-langserver", "--stdio"],
        root_uri="file:///workspace/project",
    )
    diagnostics = await lsp.diagnose("src/main.py")
    completions = await lsp.complete("src/main.py", line=10, character=4)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LSPPosition:
    """A zero-indexed line/character position in a text document."""

    line: int
    character: int


@dataclass(frozen=True)
class LSPRange:
    """A range in a text document (start inclusive, end exclusive)."""

    start: LSPPosition
    end: LSPPosition


@dataclass(frozen=True)
class LSPDiagnostic:
    """A single diagnostic (error, warning, hint) from the language server.

    Attributes:
        message:  Human-readable diagnostic description.
        severity: ``"error"``, ``"warning"``, ``"information"``, or ``"hint"``.
        range:    The text range the diagnostic applies to.
        source:   The name of the diagnostic source (e.g. ``"pyright"``).
        code:     Optional error code.
    """

    message: str
    severity: str = "error"
    range: LSPRange = field(default_factory=lambda: LSPRange(LSPPosition(0, 0), LSPPosition(0, 0)))
    source: str = ""
    code: str | None = None


@dataclass
class LSPCompletionItem:
    """A single completion suggestion from the language server."""

    label: str
    kind: str = "text"
    detail: str = ""
    documentation: str = ""


# ---------------------------------------------------------------------------
# Module-level patchable callables
# ---------------------------------------------------------------------------

def _call_lsp_complete(bridge: Any, uri: str, pos: LSPPosition) -> list[LSPCompletionItem]:
    """Request completions at *pos* in *uri* (patchable)."""
    if hasattr(bridge, "complete"):
        try:
            raw = bridge.complete(uri=uri, line=pos.line, character=pos.character)
            return [LSPCompletionItem(label=str(r)) for r in (raw or [])]
        except Exception:  # noqa: BLE001
            pass
    return []


def _call_lsp_diagnose(bridge: Any, uri: str) -> list[LSPDiagnostic]:
    """Request diagnostics for *uri* (patchable)."""
    if hasattr(bridge, "diagnose"):
        try:
            raw = bridge.diagnose(uri=uri)
            results: list[LSPDiagnostic] = []
            for r in (raw or []):
                if isinstance(r, dict):
                    results.append(
                        LSPDiagnostic(
                            message=r.get("message", ""),
                            severity=r.get("severity", "error"),
                            source=r.get("source", ""),
                            code=r.get("code"),
                        )
                    )
                elif isinstance(r, LSPDiagnostic):
                    results.append(r)
            return results
        except Exception:  # noqa: BLE001
            pass
    return []


# ---------------------------------------------------------------------------
# LSPIntegration façade
# ---------------------------------------------------------------------------


class LSPIntegration:
    """Bridges a Language Server to a JiuwenSwarm agent.

    Use :meth:`attach` to create.  After attaching, the agent can call
    the LSP as a tool to get diagnostics and completions.

    Example::

        lsp = LSPIntegration.attach(
            agent,
            server_cmd=["pyright-langserver", "--stdio"],
        )
        diags = await lsp.diagnose("src/utils.py")
        for d in diags:
            print(f"[{d.severity}] {d.message}")
    """

    def __init__(self, agent: Any, bridge: Any, server_cmd: list[str]) -> None:
        self._agent = agent
        self._bridge = bridge
        self._server_cmd = server_cmd

    @classmethod
    def attach(
        cls,
        agent: Any,
        server_cmd: list[str] | str,
        *,
        root_uri: str = "",
        language_id: str = "python",
    ) -> "LSPIntegration":
        """Attach a language server to *agent*.

        Args:
            agent:       An :class:`~openjiuwen.sdk.agent.Agent` instance.
            server_cmd:  Command to start the language server (e.g. ``["pyright-langserver", "--stdio"]``).
            root_uri:    ``file://`` URI of the project root.
            language_id: Language identifier (``"python"``, ``"typescript"``, …).

        Returns:
            :class:`LSPIntegration` bound to *agent*.
        """
        if isinstance(server_cmd, str):
            server_cmd = [server_cmd]

        bridge = _build_bridge(server_cmd, root_uri, language_id)
        return cls(agent, bridge, server_cmd)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def complete(
        self,
        uri: str,
        *,
        line: int = 0,
        character: int = 0,
    ) -> list[LSPCompletionItem]:
        """Request completions at a position in a source file.

        Args:
            uri:       File URI (e.g. ``"src/main.py"`` or ``"file:///path/src/main.py"``).
            line:      Zero-indexed line number.
            character: Zero-indexed column number.

        Returns:
            List of :class:`LSPCompletionItem` objects.
        """
        import asyncio

        pos = LSPPosition(line=line, character=character)
        return await asyncio.to_thread(_call_lsp_complete, self._bridge, uri, pos)

    async def diagnose(self, uri: str) -> list[LSPDiagnostic]:
        """Request diagnostics (type errors, lint warnings) for a file.

        Args:
            uri: File path or ``file://`` URI.

        Returns:
            List of :class:`LSPDiagnostic` objects.
        """
        import asyncio

        return await asyncio.to_thread(_call_lsp_diagnose, self._bridge, uri)

    async def shutdown(self) -> None:
        """Shut down the language server cleanly."""
        if hasattr(self._bridge, "shutdown"):
            import asyncio

            await asyncio.to_thread(self._bridge.shutdown)

    def __repr__(self) -> str:
        return f"LSPIntegration(server_cmd={self._server_cmd!r})"


# ---------------------------------------------------------------------------
# Bridge construction
# ---------------------------------------------------------------------------


def _build_bridge(server_cmd: list[str], root_uri: str, language_id: str) -> Any:
    """Build the LSP bridge using the runtime if available."""
    try:
        from openjiuwen.harness import lsp as _lsp
        from openjiuwen.harness.lsp import InitializeOptions

        import asyncio

        async def _init() -> Any:
            await _lsp.initialize_lsp(
                options=InitializeOptions(
                    server_command=server_cmd,
                    root_uri=root_uri,
                    language_id=language_id,
                )
            )
            return _lsp

        loop = asyncio.get_event_loop()
        if loop.is_running():
            return _FallbackLSPBridge(server_cmd)
        return loop.run_until_complete(_init())
    except Exception:  # noqa: BLE001
        return _FallbackLSPBridge(server_cmd)


class _FallbackLSPBridge:
    """Stub bridge used when the runtime LSP is not available."""

    def __init__(self, server_cmd: list[str]) -> None:
        self._server_cmd = server_cmd

    def complete(self, uri: str, line: int, character: int) -> list[Any]:
        return []

    def diagnose(self, uri: str) -> list[Any]:
        return []

    def shutdown(self) -> None:
        pass
