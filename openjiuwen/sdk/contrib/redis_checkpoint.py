"""Redis checkpoint backend for the JiuwenSwarm SDK.

Requires ``redis-py`` (``pip install openjiuwen-sdk[redis]``).

Example::

    from openjiuwen.sdk.contrib.redis_checkpoint import RedisCheckpointBackend
    from openjiuwen.sdk.extensions import register_checkpointer

    backend = RedisCheckpointBackend(url="redis://localhost:6379/0")
    register_checkpointer("redis", backend)

    agent = await Agent.create("my-agent", ..., checkpoint_store="redis")
"""

from __future__ import annotations

import json
from typing import Any

from openjiuwen.sdk.contrib.memory_checkpoint import CheckpointerBackend
from openjiuwen.sdk.errors import CheckpointError


class RedisCheckpointBackend(CheckpointerBackend):
    """Redis-backed persistent checkpoint store.

    Uses ``redis-py`` for both synchronous (via ``asyncio``) and async access.
    Checkpoints are stored as JSON strings under keys of the form
    ``jiuwenswarm:checkpoint:<checkpoint_id>``.

    Args:
        url:        Redis connection URL (e.g. ``"redis://localhost:6379/0"``).
        key_prefix: Redis key prefix (default: ``"jiuwenswarm:checkpoint:"``)
        ttl:        Optional time-to-live in seconds (``None`` means no expiry).

    Raises:
        :class:`ImportError`: If ``redis`` is not installed.

    Example::

        backend = RedisCheckpointBackend(url="redis://localhost:6379")
        await backend.save("ckpt_abc", {"agent": "coder", "step": 3})
        state = await backend.load("ckpt_abc")
    """

    def __init__(
        self,
        url: str = "redis://localhost:6379/0",
        *,
        key_prefix: str = "jiuwenswarm:checkpoint:",
        ttl: int | None = None,
    ) -> None:
        try:
            import redis.asyncio as aioredis

            self._client: Any = aioredis.from_url(url)
        except ImportError as exc:
            raise ImportError(
                "redis-py is not installed.  "
                "Install it with: pip install openjiuwen-sdk[redis]"
            ) from exc

        self._prefix = key_prefix
        self._ttl = ttl

    def _key(self, checkpoint_id: str) -> str:
        return f"{self._prefix}{checkpoint_id}"

    async def save(self, checkpoint_id: str, state: dict[str, Any]) -> None:
        """Persist *state* to Redis under *checkpoint_id*.

        Args:
            checkpoint_id: Opaque identifier.
            state:         JSON-serialisable state dict.
        """
        try:
            serialised = json.dumps(state)
            if self._ttl is not None:
                await self._client.setex(self._key(checkpoint_id), self._ttl, serialised)
            else:
                await self._client.set(self._key(checkpoint_id), serialised)
        except Exception as exc:  # noqa: BLE001
            raise CheckpointError(f"Redis save failed: {exc}") from exc

    async def load(self, checkpoint_id: str) -> dict[str, Any]:
        """Load *checkpoint_id* from Redis.

        Raises:
            :class:`~openjiuwen.sdk.errors.CheckpointError`: If not found or corrupt.
        """
        try:
            data = await self._client.get(self._key(checkpoint_id))
        except Exception as exc:  # noqa: BLE001
            raise CheckpointError(f"Redis load failed: {exc}") from exc

        if data is None:
            raise CheckpointError(
                f"Checkpoint '{checkpoint_id}' not found in Redis."
            )
        try:
            return json.loads(data)
        except json.JSONDecodeError as exc:
            raise CheckpointError(
                f"Checkpoint '{checkpoint_id}' data is corrupt: {exc}"
            ) from exc

    async def list(self) -> list[str]:
        """Return all checkpoint IDs stored in Redis (under the configured prefix)."""
        try:
            keys = await self._client.keys(f"{self._prefix}*")
            return [k.decode("utf-8").removeprefix(self._prefix) for k in keys]
        except Exception as exc:  # noqa: BLE001
            raise CheckpointError(f"Redis list failed: {exc}") from exc

    async def delete(self, checkpoint_id: str) -> None:
        """Delete *checkpoint_id* from Redis (no-op if not found)."""
        try:
            await self._client.delete(self._key(checkpoint_id))
        except Exception as exc:  # noqa: BLE001
            raise CheckpointError(f"Redis delete failed: {exc}") from exc

    async def close(self) -> None:
        """Close the Redis connection."""
        await self._client.aclose()

    def __repr__(self) -> str:
        return f"RedisCheckpointBackend(prefix={self._prefix!r}, ttl={self._ttl})"
