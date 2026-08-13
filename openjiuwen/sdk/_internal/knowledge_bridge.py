"""In-process knowledge base bridge.

Wraps ``openjiuwen.core`` knowledge/retrieval primitives so that the
:class:`~openjiuwen.sdk.knowledge.KnowledgeBase` façade can drive them through
a stable internal API.

All public callables here are module-level so tests can monkeypatch them.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any


# ---------------------------------------------------------------------------
# Module-level patchable callables
# ---------------------------------------------------------------------------


def create_knowledge_base(
    name: str,
    embedding_model: str,
    vector_store: str,
) -> Any:
    """Create a knowledge base via the runtime (patchable)."""
    try:
        from openjiuwen.core.retrieval import KnowledgeBase, KnowledgeBaseConfig

        cfg = KnowledgeBaseConfig(
            name=name,
            embedding_model=embedding_model,
            vector_store=vector_store,
        )
        return KnowledgeBase(config=cfg)
    except ImportError:
        return _FallbackKnowledgeStore(name=name, embedding_model=embedding_model)


def add_documents(store: Any, documents: list[dict[str, Any]]) -> None:
    """Index *documents* into *store* (patchable)."""
    if isinstance(store, _FallbackKnowledgeStore):
        for doc in documents:
            store.add(doc)
        return
    try:
        from openjiuwen.core.retrieval import Document as _Doc

        rt_docs = [
            _Doc(text=d.get("text", ""), metadata=d.get("metadata", {}))
            for d in documents
        ]
        import asyncio

        loop = asyncio.get_event_loop()
        loop.run_until_complete(store.add_documents(rt_docs))
    except Exception as exc:  # noqa: BLE001
        from openjiuwen.sdk.errors import SdkError

        raise SdkError(f"knowledge.add_documents failed: {exc}") from exc


async def add_documents_async(store: Any, documents: list[dict[str, Any]]) -> None:
    """Async version of :func:`add_documents` (patchable)."""
    if isinstance(store, _FallbackKnowledgeStore):
        for doc in documents:
            store.add(doc)
        return
    try:
        from openjiuwen.core.retrieval import Document as _Doc

        rt_docs = [
            _Doc(text=d.get("text", ""), metadata=d.get("metadata", {}))
            for d in documents
        ]
        await store.add_documents(rt_docs)
    except ImportError:
        for doc in documents:
            store._entries.append(doc)
    except Exception as exc:  # noqa: BLE001
        from openjiuwen.sdk.errors import SdkError

        raise SdkError(f"knowledge.add_documents failed: {exc}") from exc


async def query_knowledge_base(
    store: Any, query: str, top_k: int
) -> list[dict[str, Any]]:
    """Query *store* for chunks relevant to *query* (patchable)."""
    if isinstance(store, _FallbackKnowledgeStore):
        return store.query(query, top_k)
    try:
        results = await store.query(query, top_k=top_k)
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
        from openjiuwen.sdk.errors import SdkError

        raise SdkError(f"knowledge.query failed: {exc}") from exc


# Graph KB-specific
async def add_entity(
    store: Any, entity_id: str, text: str, links: list[str]
) -> None:
    """Add an entity to a graph knowledge store (patchable)."""
    if isinstance(store, _FallbackKnowledgeStore):
        store._graph[entity_id] = {"text": text, "links": links}
        return
    try:
        await store.add_entity(entity_id, text=text, links=links)
    except Exception as exc:  # noqa: BLE001
        from openjiuwen.sdk.errors import SdkError

        raise SdkError(f"graph_kb.add_entity failed: {exc}") from exc


async def graph_query(
    store: Any, query: str, top_k: int, use_graph: bool
) -> list[dict[str, Any]]:
    """Query a graph knowledge store (patchable)."""
    if isinstance(store, _FallbackKnowledgeStore):
        results = store.query(query, top_k)
        if use_graph:
            for entity_id, entity in store._graph.items():
                if query.lower() in entity["text"].lower():
                    results.append({"text": entity["text"], "score": 0.8, "metadata": {"entity_id": entity_id}})
        return results[:top_k]
    try:
        results = await store.retrieve(query, top_k=top_k, use_graph=use_graph)
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
        from openjiuwen.sdk.errors import SdkError

        raise SdkError(f"graph_kb.query failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Fallback in-memory implementation
# ---------------------------------------------------------------------------


@dataclass
class _FallbackKnowledgeStore:
    """Simple in-memory knowledge store used when runtime is not installed."""

    name: str
    embedding_model: str
    _entries: list[dict[str, Any]] = field(default_factory=list, init=False, repr=False)
    _graph: dict[str, dict[str, Any]] = field(default_factory=dict, init=False, repr=False)

    def add(self, doc: dict[str, Any]) -> None:
        entry_id = f"doc_{uuid.uuid4().hex[:8]}"
        self._entries.append({"id": entry_id, **doc, "score": 1.0})

    def query(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        q = query.lower()
        matched = [e for e in self._entries if q in e.get("text", "").lower()]
        return matched[:top_k] if matched else self._entries[:top_k]
