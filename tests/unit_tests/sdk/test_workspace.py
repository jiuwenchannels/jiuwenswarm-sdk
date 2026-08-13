"""Unit tests for openjiuwen.sdk.workspace — Workspace file-system façade."""

from __future__ import annotations

import pytest

from openjiuwen.sdk.errors import SdkError
from openjiuwen.sdk.workspace import Workspace, WorkspaceConfig


# ---------------------------------------------------------------------------
# WorkspaceConfig tests
# ---------------------------------------------------------------------------


def test_workspace_config_defaults():
    cfg = WorkspaceConfig()
    assert cfg.root == "."
    assert cfg.sandbox is False
    assert cfg.sandbox_image == "python:3.11-slim"
    assert cfg.max_file_size == 10 * 1024 * 1024
    assert cfg.allowed_extensions == ()


def test_workspace_config_from_config():
    cfg = WorkspaceConfig(root="/tmp", max_file_size=1024)
    ws = Workspace(config=cfg)
    assert ws._max_file_size == 1024


# ---------------------------------------------------------------------------
# Workspace construction
# ---------------------------------------------------------------------------


def test_workspace_default_root(tmp_path):
    ws = Workspace(root=tmp_path)
    assert ws.root == tmp_path


def test_workspace_repr(tmp_path):
    ws = Workspace(root=tmp_path)
    rep = repr(ws)
    assert "Workspace" in rep
    assert "sandbox=False" in rep


# ---------------------------------------------------------------------------
# Path safety
# ---------------------------------------------------------------------------


def test_workspace_path_traversal_raises(tmp_path):
    ws = Workspace(root=tmp_path)
    with pytest.raises(SdkError, match="escapes"):
        ws._safe_path("../../etc/passwd")


def test_workspace_safe_path_ok(tmp_path):
    ws = Workspace(root=tmp_path)
    result = ws._safe_path("subdir/file.txt")
    assert result.parts[-2:] == ("subdir", "file.txt")


# ---------------------------------------------------------------------------
# File read / write
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_workspace_write_read_roundtrip(tmp_path):
    ws = Workspace(root=tmp_path)
    await ws.write("hello.txt", "Hello, World!")
    content = await ws.read("hello.txt")
    assert content == "Hello, World!"


@pytest.mark.asyncio
async def test_workspace_write_creates_directories(tmp_path):
    ws = Workspace(root=tmp_path)
    await ws.write("deep/nested/file.txt", "data")
    assert (tmp_path / "deep" / "nested" / "file.txt").exists()


@pytest.mark.asyncio
async def test_workspace_read_nonexistent_raises(tmp_path):
    ws = Workspace(root=tmp_path)
    with pytest.raises(SdkError, match="not found"):
        await ws.read("missing.txt")


@pytest.mark.asyncio
async def test_workspace_modified_files_tracking(tmp_path):
    ws = Workspace(root=tmp_path)
    # First write creates the file
    await ws.write("a.txt", "initial")
    assert "a.txt" in ws.created_files
    assert "a.txt" not in ws.modified_files

    # Second write marks as modified
    await ws.write("a.txt", "updated")
    assert "a.txt" in ws.modified_files


@pytest.mark.asyncio
async def test_workspace_created_files_tracking(tmp_path):
    ws = Workspace(root=tmp_path)
    await ws.write("new.txt", "content")
    assert "new.txt" in ws.created_files


# ---------------------------------------------------------------------------
# run_command
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_workspace_run_command_echo(tmp_path):
    ws = Workspace(root=tmp_path)
    output = await ws.run_command("echo hello")
    assert "hello" in output


@pytest.mark.asyncio
async def test_workspace_run_command_list(tmp_path):
    ws = Workspace(root=tmp_path)
    (tmp_path / "testfile").touch()
    output = await ws.run_command(["ls", str(tmp_path)])
    assert "testfile" in output
