"""In-process memory bridge.

Wraps ``openjiuwen.core`` memory primitives so that the
:class:`~openjiuwen.sdk.knowledge.memory.Memory` façade can drive them through a stable
internal API without leaking internals into the public surface.

All public callables here are module-level so that tests can monkeypatch them.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    pass

# ---------------------------------------------------------------------------
# Module-level patchable callables
# ---------------------------------------------------------------------------


def create_memory_store(scope: str, user_id: str | None) -> Any:
    """Create a memory store via the runtime (patchable)."""
    try:
        from openjiuwen.core.memory import MemoryStore

        return MemoryStore(scope=scope, user_id=user_id)
    except ImportError:
        return _FallbackMemoryStore(scope=scope, user_id=user_id)


def add_memory(store: Any, text: str, metadata: dict[str, Any] | None) -> str:
    """Add a memory entry to *store* (patchable)."""
    if isinstance(store, _FallbackMemoryStore):
        return store.add(text, metadata)
    try:
        result = store.add(text, metadata=metadata or {})
        if hasattr(result, "id"):
            return str(result.id)
        return str(result)
    except Exception as exc:  # noqa: BLE001
        from openjiuwen.sdk.core.errors import SdkError

        raise SdkError(f"memory.add failed: {exc}") from exc


def search_memory(store: Any, query: str, top_k: int) -> list[dict[str, Any]]:
    """Search *store* for entries matching *query* (patchable).

    Returns a list of dicts with ``text``, ``score``, and ``metadata`` keys.
    """
    if isinstance(store, _FallbackMemoryStore):
        return store.search(query, top_k)
    try:
        results = store.search(query, top_k=top_k)
        out: list[dict[str, Any]] = []
        for r in results:
            if isinstance(r, dict):
                out.append(r)
            else:
                out.append(
                    {
                        "text": getattr(r, "text", str(r)),
                        "score": getattr(r, "score", 1.0),
                        "metadata": getattr(r, "metadata", {}),
                    }
                )
        return out
    except Exception as exc:  # noqa: BLE001
        from openjiuwen.sdk.core.errors import SdkError

        raise SdkError(f"memory.search failed: {exc}") from exc


def clear_memory(store: Any) -> None:
    """Remove all entries from *store* (patchable)."""
    if isinstance(store, _FallbackMemoryStore):
        store.clear()
        return
    try:
        store.clear()
    except Exception as exc:  # noqa: BLE001
        from openjiuwen.sdk.core.errors import SdkError

        raise SdkError(f"memory.clear failed: {exc}") from exc


# ---------------------------------------------------------------------------
# In-process fallback (used when runtime is not installed)
# ---------------------------------------------------------------------------


@dataclass
class _FallbackMemoryStore:
    """Simple in-memory store used when the runtime is unavailable."""

    scope: str
    user_id: str | None
    _entries: list[dict[str, Any]] = field(default_factory=list, init=False, repr=False)

    def add(self, text: str, metadata: dict[str, Any] | None = None) -> str:
        entry_id = f"mem_{uuid.uuid4().hex[:8]}"
        self._entries.append(
            {"id": entry_id, "text": text, "score": 1.0, "metadata": metadata or {}}
        )
        return entry_id

    def search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Naive substring search over stored text."""
        q = query.lower()
        matched = [e for e in self._entries if q in e["text"].lower()]
        return matched[:top_k] if matched else self._entries[:top_k]

    def clear(self) -> None:
        self._entries.clear()
