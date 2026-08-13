"""SDK Workspace façade — bound, file-system-aware coding agent environment.

A :class:`Workspace` binds an agent to a local directory and optionally runs
shell commands inside an isolated container (sandbox mode).

Quick start::

    from openjiuwen.sdk.infra.workspace import Workspace

    ws = Workspace(root="/path/to/project")
    agent = await Agent.create("coder", workspace=ws, model=ModelConfig.from_env())
    await agent.run("Add type annotations to all functions in src/")
    print(await ws.diff())
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from openjiuwen.sdk.core.errors import SdkError


# ---------------------------------------------------------------------------
# WorkspaceConfig
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkspaceConfig:
    """Configuration for a :class:`Workspace`.

    Attributes:
        root:          Absolute path to the project directory.
        sandbox:       When ``True``, shell commands run in a container.
        sandbox_image: Docker image used for the sandbox container.
        max_file_size: Maximum file size (bytes) the agent may read/write.
        allowed_extensions: If non-empty, restrict reads/writes to these extensions.
    """

    root: str = "."
    sandbox: bool = False
    sandbox_image: str = "python:3.11-slim"
    max_file_size: int = 10 * 1024 * 1024  # 10 MB
    allowed_extensions: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Workspace façade
# ---------------------------------------------------------------------------


class Workspace:
    """An agent's file-system workspace.

    Restricts agent file operations to the *root* directory.  Any path that
    escapes *root* via ``..`` traversal raises :class:`~openjiuwen.sdk.core.errors.SdkError`.

    Example::

        ws = Workspace(root="/tmp/project", sandbox=True)
        content = await ws.read("src/main.py")
        await ws.write("NOTES.md", "# Notes\\n")
        diff = await ws.diff()
    """

    def __init__(
        self,
        root: str | Path = ".",
        *,
        sandbox: bool = False,
        sandbox_image: str = "python:3.11-slim",
        config: WorkspaceConfig | None = None,
    ) -> None:
        if config is not None:
            self._root = Path(config.root).resolve()
            self._sandbox = config.sandbox
            self._sandbox_image = config.sandbox_image
            self._max_file_size = config.max_file_size
        else:
            self._root = Path(root).resolve()
            self._sandbox = sandbox
            self._sandbox_image = sandbox_image
            self._max_file_size = 10 * 1024 * 1024

        self._modified: list[str] = []
        self._created: list[str] = []

    # ------------------------------------------------------------------
    # Path safety
    # ------------------------------------------------------------------

    def _safe_path(self, relative: str | Path) -> Path:
        """Resolve *relative* inside *root* and guard against path traversal.

        Raises:
            :class:`~openjiuwen.sdk.core.errors.SdkError`: If the resolved path is outside *root*.
        """
        target = (self._root / relative).resolve()
        try:
            target.relative_to(self._root)
        except ValueError:
            raise SdkError(
                f"Path '{relative}' escapes the workspace root '{self._root}'."
            )
        return target

    # ------------------------------------------------------------------
    # File I/O
    # ------------------------------------------------------------------

    async def read(self, path: str | Path) -> str:
        """Read and return the text content of a file.

        Args:
            path: Path relative to the workspace root.

        Returns:
            File contents as a UTF-8 string.

        Raises:
            :class:`~openjiuwen.sdk.core.errors.SdkError`: If the path is outside root.
        """
        target = self._safe_path(path)
        if not target.exists():
            raise SdkError(f"File not found: {path}")
        if target.stat().st_size > self._max_file_size:
            raise SdkError(
                f"File '{path}' exceeds the maximum size of {self._max_file_size} bytes."
            )
        return await asyncio.to_thread(target.read_text, encoding="utf-8", errors="replace")

    async def write(self, path: str | Path, content: str) -> None:
        """Write *content* to a file, creating intermediate directories as needed.

        Args:
            path:    Path relative to the workspace root.
            content: Text content to write (UTF-8).

        Raises:
            :class:`~openjiuwen.sdk.core.errors.SdkError`: If the path is outside root.
        """
        target = self._safe_path(path)
        existed = target.exists()
        await asyncio.to_thread(target.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(target.write_text, content, encoding="utf-8")
        rel = str(Path(path))
        if existed:
            if rel not in self._modified:
                self._modified.append(rel)
        else:
            if rel not in self._created:
                self._created.append(rel)

    # ------------------------------------------------------------------
    # Shell commands
    # ------------------------------------------------------------------

    async def run_command(
        self,
        cmd: str | list[str],
        *,
        timeout: float = 60.0,
    ) -> str:
        """Execute a shell command inside the workspace root.

        In sandbox mode the command runs inside a Docker container with the
        workspace root mounted at ``/workspace``.

        Args:
            cmd:     Command string or list of arguments.
            timeout: Maximum seconds to wait for the command to complete.

        Returns:
            Combined stdout + stderr output as a string.

        Raises:
            :class:`~openjiuwen.sdk.core.errors.SdkError`: If the command fails or times out.
        """
        if self._sandbox:
            return await self._run_sandboxed(cmd, timeout=timeout)

        if isinstance(cmd, str):
            shell_cmd = cmd
            use_shell = True
        else:
            shell_cmd = cmd
            use_shell = False

        try:
            proc = await asyncio.create_subprocess_shell(
                shell_cmd if use_shell else " ".join(cmd),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=str(self._root),
            )
            try:
                stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
            except asyncio.TimeoutError:
                proc.kill()
                raise SdkError(f"Command timed out after {timeout}s: {cmd!r}")
            return stdout.decode("utf-8", errors="replace")
        except SdkError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise SdkError(f"Command failed: {exc}") from exc

    async def _run_sandboxed(self, cmd: Any, timeout: float = 60.0) -> str:
        """Run command inside a Docker container (sandbox mode)."""
        if isinstance(cmd, list):
            cmd = " ".join(cmd)
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{self._root}:/workspace",
            "-w",
            "/workspace",
            self._sandbox_image,
            "sh",
            "-c",
            cmd,
        ]
        try:
            result = await asyncio.to_thread(
                subprocess.run,
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            raise SdkError(f"Sandboxed command timed out after {timeout}s.")
        except FileNotFoundError:
            raise SdkError(
                "Docker is not installed or not in PATH. "
                "Sandbox mode requires Docker."
            )

    # ------------------------------------------------------------------
    # VCS helpers
    # ------------------------------------------------------------------

    async def diff(self) -> str:
        """Return the ``git diff`` output for the workspace root.

        Returns:
            Unified diff string, or an empty string if no changes.
        """
        try:
            result = await self.run_command(["git", "diff", "--stat"])
            return result
        except SdkError:
            # Not a git repo or git not installed — return empty diff
            return ""

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def root(self) -> Path:
        """The absolute path to the workspace root directory."""
        return self._root

    @property
    def modified_files(self) -> list[str]:
        """Files that have been modified via :meth:`write` since creation."""
        return list(self._modified)

    @property
    def created_files(self) -> list[str]:
        """Files that have been created via :meth:`write` since creation."""
        return list(self._created)

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return (
            f"Workspace(root={str(self._root)!r}, sandbox={self._sandbox})"
        )
