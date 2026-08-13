"""SDK Memory façade — persistent long-term memory for agents.

Memory can be scoped to an individual user or shared across a team:

* :attr:`MemoryScope.USER` — one memory store per ``user_id``.
* :attr:`MemoryScope.AGENT` — one memory store per agent name.
* :attr:`MemoryScope.SESSION` — one memory store per session ID.
* :attr:`MemoryScope.GLOBAL` — a single global store.

Quick start::

    from openjiuwen.sdk import Agent, ModelConfig
    from openjiuwen.sdk.memory import MemoryScope

    agent = await Agent.create(
        "assistant",
        model=ModelConfig.from_env(),
        memory_scope=MemoryScope.USER,
        user_id="user_42",
    )

    await agent.memory.add("User prefers bullet-point responses.")
    records = await agent.memory.search("preferences")
    for r in records:
        print(f"[{r.score:.2f}] {r.text}")
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

from openjiuwen.sdk._internal import memory_bridge as _mb


# ---------------------------------------------------------------------------
# MemoryScope
# ---------------------------------------------------------------------------


class MemoryScope(str, enum.Enum):
    """Defines the isolation boundary for an agent's memory store."""

    USER = "user"
    AGENT = "agent"
    SESSION = "session"
    GLOBAL = "global"


# ---------------------------------------------------------------------------
# MemoryRecord — returned by Memory.search()
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MemoryRecord:
    """A single memory entry returned by a search.

    Attributes:
        text:     The stored text.
        score:    Relevance score in [0, 1].
        metadata: Arbitrary key-value metadata attached at write time.
        id:       Opaque entry ID.
    """

    text: str
    score: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str | None = None


# ---------------------------------------------------------------------------
# Memory façade
# ---------------------------------------------------------------------------


class Memory:
    """Manages the persistent memory store attached to one agent.

    Do **not** instantiate directly.  Access via ``agent.memory`` after the
    agent is created with a :class:`MemoryScope`.

    Example::

        records = await agent.memory.search("user preferences")
        for r in records:
            print(r.text)
    """

    def __init__(
        self,
        scope: MemoryScope = MemoryScope.USER,
        user_id: str | None = None,
    ) -> None:
        self._scope = scope
        self._user_id = user_id
        self._store: Any = _mb.create_memory_store(scope.value, user_id)

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def add(
        self,
        text: str,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Store *text* in memory and return its opaque entry ID.

        Args:
            text:     The text to store.
            metadata: Optional key-value metadata (source, timestamp, …).

        Returns:
            Opaque entry ID (string).
        """
        return _mb.add_memory(self._store, text, metadata)

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def search(
        self,
        query: str,
        *,
        top_k: int = 5,
    ) -> list[MemoryRecord]:
        """Return the *top_k* most relevant memory entries for *query*.

        Args:
            query: Natural-language query string.
            top_k: Maximum number of results to return.

        Returns:
            List of :class:`MemoryRecord` objects, sorted by relevance (highest first).
        """
        raw = _mb.search_memory(self._store, query, top_k)
        records: list[MemoryRecord] = []
        for item in raw:
            records.append(
                MemoryRecord(
                    text=item.get("text", ""),
                    score=float(item.get("score", 1.0)),
                    metadata=item.get("metadata", {}),
                    id=item.get("id"),
                )
            )
        return records

    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------

    async def clear(self) -> None:
        """Remove all entries from this memory store."""
        _mb.clear_memory(self._store)

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Memory(scope={self._scope.value!r}, user_id={self._user_id!r})"


# ---------------------------------------------------------------------------
# Factory helper used by Agent
# ---------------------------------------------------------------------------


def make_memory(
    scope: MemoryScope | None,
    user_id: str | None = None,
) -> Memory | None:
    """Create a :class:`Memory` instance for *scope*, or ``None`` if no scope given."""
    if scope is None:
        return None
    return Memory(scope=scope, user_id=user_id)
