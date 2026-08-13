"""Abstract checkpointer interface for custom backends.

Implement :class:`BaseCheckpointer` to plug in your own checkpoint storage
(S3, GCS, PostgreSQL, …).

Example::

    from openjiuwen.sdk.extensions.checkpointer import BaseCheckpointer
    from openjiuwen.sdk.extensions import register_checkpointer

    class S3Checkpointer(BaseCheckpointer):
        async def save(self, checkpoint_id: str, state: dict) -> None: ...
        async def load(self, checkpoint_id: str) -> dict: ...

    register_checkpointer("s3", S3Checkpointer(bucket="my-checkpoints"))
"""

from __future__ import annotations

import abc
from typing import Any


class BaseCheckpointer(abc.ABC):
    """Abstract interface for custom checkpoint backends.

    Subclass and implement :meth:`save` and :meth:`load`, then register with::

        from openjiuwen.sdk.extensions import register_checkpointer
        register_checkpointer("my-backend", MyCheckpointer(...))

    The SDK calls ``save`` / ``load`` with opaque string IDs and JSON-serialisable
    state dicts.
    """

    @abc.abstractmethod
    async def save(self, checkpoint_id: str, state: dict[str, Any]) -> None:
        """Persist *state* under *checkpoint_id*.

        Args:
            checkpoint_id: Opaque identifier (e.g. ``"ckpt_abc123"``).
            state:         JSON-serialisable agent state dict.
        """

    @abc.abstractmethod
    async def load(self, checkpoint_id: str) -> dict[str, Any]:
        """Return the state for *checkpoint_id*.

        Args:
            checkpoint_id: The opaque identifier returned by :meth:`save`.

        Returns:
            The state dict previously passed to :meth:`save`.

        Raises:
            :class:`~openjiuwen.sdk.core.errors.CheckpointError`: If not found.
        """
