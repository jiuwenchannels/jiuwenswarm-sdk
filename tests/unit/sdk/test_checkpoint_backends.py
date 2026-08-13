"""Unit tests for openjiuwen.sdk.contrib.memory_checkpoint."""

from __future__ import annotations

import pytest

from openjiuwen.sdk.contrib.memory_checkpoint import (
    CheckpointerBackend,
    InMemoryCheckpointBackend,
)
from openjiuwen.sdk.core.errors import CheckpointError


# ---------------------------------------------------------------------------
# CheckpointerBackend interface
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_base_backend_raises_not_implemented():
    backend = CheckpointerBackend()
    with pytest.raises(NotImplementedError):
        await backend.save("ckpt", {})
    with pytest.raises(NotImplementedError):
        await backend.load("ckpt")
    with pytest.raises(NotImplementedError):
        await backend.list()
    with pytest.raises(NotImplementedError):
        await backend.delete("ckpt")


# ---------------------------------------------------------------------------
# InMemoryCheckpointBackend
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_inmemory_save_and_load():
    backend = InMemoryCheckpointBackend()
    await backend.save("ckpt_001", {"agent": "researcher", "turn": 5})
    state = await backend.load("ckpt_001")
    assert state["turn"] == 5
    assert state["agent"] == "researcher"


@pytest.mark.asyncio
async def test_inmemory_load_missing_raises():
    backend = InMemoryCheckpointBackend()
    with pytest.raises(CheckpointError, match="not found"):
        await backend.load("nonexistent")


@pytest.mark.asyncio
async def test_inmemory_list_empty():
    backend = InMemoryCheckpointBackend()
    ids = await backend.list()
    assert ids == []


@pytest.mark.asyncio
async def test_inmemory_list_after_save():
    backend = InMemoryCheckpointBackend()
    await backend.save("a", {"x": 1})
    await backend.save("b", {"x": 2})
    ids = await backend.list()
    assert set(ids) == {"a", "b"}


@pytest.mark.asyncio
async def test_inmemory_delete():
    backend = InMemoryCheckpointBackend()
    await backend.save("ckpt", {"val": 42})
    await backend.delete("ckpt")
    with pytest.raises(CheckpointError):
        await backend.load("ckpt")


@pytest.mark.asyncio
async def test_inmemory_delete_missing_noop():
    backend = InMemoryCheckpointBackend()
    # Should not raise
    await backend.delete("does_not_exist")


@pytest.mark.asyncio
async def test_inmemory_state_top_level_keys_are_copied():
    """Top-level dict keys are shallow-copied — adding a new key to the
    original dict should not affect the saved state."""
    backend = InMemoryCheckpointBackend()
    state = {"turn": 1}
    await backend.save("c", state)
    # Add a new top-level key to original
    state["extra"] = "new"
    loaded = await backend.load("c")
    assert "extra" not in loaded
    assert loaded["turn"] == 1


def test_inmemory_len():
    backend = InMemoryCheckpointBackend()
    assert len(backend) == 0


@pytest.mark.asyncio
async def test_inmemory_len_after_saves():
    backend = InMemoryCheckpointBackend()
    await backend.save("x", {})
    await backend.save("y", {})
    assert len(backend) == 2


def test_inmemory_repr():
    backend = InMemoryCheckpointBackend()
    rep = repr(backend)
    assert "InMemoryCheckpointBackend" in rep
