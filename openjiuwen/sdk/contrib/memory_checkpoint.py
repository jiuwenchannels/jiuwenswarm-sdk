"""In-memory checkpoint backend for the JiuwenSwarm SDK.

This backend stores checkpoints in a Python dict (process-local, non-persistent).
Useful for testing and development.

Example::

    from openjiuwen.sdk.contrib.memory_checkpoint import InMemoryCheckpointBackend
    from openjiuwen.sdk.extensions import register_checkpointer

    backend = InMemoryCheckpointBackend()
    register_checkpointer("memory", backend)

    agent = await Agent.create("my-agent", ..., checkpoint_store="memory")
    ckpt_id = await agent.checkpoint()
    restored = await Agent.restore(ckpt_id)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from openjiuwen.sdk.core.errors import CheckpointError


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


class CheckpointerBackend:
    """Abstract interface for checkpoint backends.

    Subclass this to create custom checkpoint stores::

        class MyBackend(CheckpointerBackend):
            async def save(self, checkpoint_id: str, state: dict) -> None: ...
            async def load(self, checkpoint_id: str) -> dict: ...
            async def list(self) -> list[str]: ...
            async def delete(self, checkpoint_id: str) -> None: ...
    """

    async def save(self, checkpoint_id: str, state: dict[str, Any]) -> None:
        """Persist *state* under *checkpoint_id*."""
        raise NotImplementedError

    async def load(self, checkpoint_id: str) -> dict[str, Any]:
        """Return the state stored under *checkpoint_id*.

        Raises:
            :class:`~openjiuwen.sdk.core.errors.CheckpointError`: If not found.
        """
        raise NotImplementedError

    async def list(self) -> list[str]:
        """Return all stored checkpoint IDs."""
        raise NotImplementedError

    async def delete(self, checkpoint_id: str) -> None:
        """Remove *checkpoint_id* from the store."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# InMemoryCheckpointBackend
# ---------------------------------------------------------------------------


class InMemoryCheckpointBackend(CheckpointerBackend):
    """Process-local, non-persistent checkpoint backend.

    Stores checkpoints in a Python dict.  All checkpoints are lost when the
    process exits.

    Example::

        backend = InMemoryCheckpointBackend()
        await backend.save("ckpt_001", {"agent": "researcher", "turn": 5})
        state = await backend.load("ckpt_001")
        assert state["turn"] == 5
    """

    def __init__(self) -> None:
        self._store: dict[str, dict[str, Any]] = {}

    async def save(self, checkpoint_id: str, state: dict[str, Any]) -> None:
        """Save *state* under *checkpoint_id*.

        Args:
            checkpoint_id: Opaque identifier for this checkpoint.
            state:         Serialisable state dict.
        """
        self._store[checkpoint_id] = dict(state)

    async def load(self, checkpoint_id: str) -> dict[str, Any]:
        """Return the state for *checkpoint_id*.

        Raises:
            :class:`~openjiuwen.sdk.core.errors.CheckpointError`: If not found.
        """
        if checkpoint_id not in self._store:
            raise CheckpointError(
                f"Checkpoint '{checkpoint_id}' not found in InMemoryCheckpointBackend."
            )
        return dict(self._store[checkpoint_id])

    async def list(self) -> list[str]:
        """Return all stored checkpoint IDs."""
        return list(self._store.keys())

    async def delete(self, checkpoint_id: str) -> None:
        """Delete *checkpoint_id* (no-op if not found)."""
        self._store.pop(checkpoint_id, None)

    def __len__(self) -> int:
        return len(self._store)

    def __repr__(self) -> str:
        return f"InMemoryCheckpointBackend(checkpoints={len(self._store)})"
