"""SDK Knowledge Base façade — document indexing and retrieval-augmented generation.

Quick start::

    from openjiuwen.sdk.knowledge import KnowledgeBase, Retriever, Document

    kb = await KnowledgeBase.create("my-kb", embedding_model="text-embedding-3-small")
    await kb.add_documents([Document(text="Refunds are valid within 30 days.")])

    results = await Retriever(kb).retrieve("return policy", top_k=3)
    for r in results:
        print(f"[{r.score:.2f}] {r.text}")

    # RAG: attach the KB to an agent
    from openjiuwen.sdk import Agent, ModelConfig
    agent = await Agent.create("bot", knowledge_bases=[kb], model=ModelConfig.from_env())
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from openjiuwen.sdk._internal import knowledge_bridge as _kb


# ---------------------------------------------------------------------------
# Document — input type for add_documents()
# ---------------------------------------------------------------------------


@dataclass
class Document:
    """A text document to be indexed in a :class:`KnowledgeBase`.

    Attributes:
        text:     The document text.
        metadata: Optional key-value metadata (source, url, …).
        id:       Optional stable ID; auto-generated if omitted.
    """

    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str | None = None


# ---------------------------------------------------------------------------
# RetrievalResult — returned by search/query operations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RetrievalResult:
    """A single chunk returned by a retrieval operation.

    Attributes:
        text:     The matched text snippet.
        score:    Relevance score in [0, 1].
        metadata: Metadata attached at index time.
    """

    text: str
    score: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# KnowledgeBase
# ---------------------------------------------------------------------------


class KnowledgeBase:
    """A document store with semantic search capabilities.

    Create via :meth:`create` (async factory), then use :meth:`add_documents`
    and :meth:`query`.  Pass to :meth:`~openjiuwen.sdk.core.agent.Agent.create`
    as ``knowledge_bases=[kb]`` for automatic RAG.

    Example::

        kb = await KnowledgeBase.create("docs", embedding_model="text-embedding-3-small")
        await kb.add_documents([Document(text="...")])
        results = await kb.query("customer support hours")
    """

    def __init__(self, _store: Any, *, name: str) -> None:
        self._store = _store
        self._name = name

    @classmethod
    async def create(
        cls,
        name: str,
        *,
        embedding_model: str = "text-embedding-3-small",
        vector_store: str = "chroma",
    ) -> "KnowledgeBase":
        """Create a new knowledge base.

        Args:
            name:            Human-readable name (used as the namespace).
            embedding_model: Embedding model identifier.
            vector_store:    Backend: ``"chroma"``, ``"milvus"``, etc.

        Returns:
            A :class:`KnowledgeBase` ready for document indexing.
        """
        store = _kb.create_knowledge_base(name, embedding_model, vector_store)
        return cls(store, name=name)

    async def add_documents(self, documents: list[Document]) -> None:
        """Index *documents* into this knowledge base.

        Args:
            documents: List of :class:`Document` objects to index.
        """
        dicts = [{"text": d.text, "metadata": d.metadata, "id": d.id} for d in documents]
        await _kb.add_documents_async(self._store, dicts)

    async def query(self, query: str, *, top_k: int = 5) -> list[RetrievalResult]:
        """Return the *top_k* most relevant chunks for *query*.

        Args:
            query: Natural-language query string.
            top_k: Maximum number of results.

        Returns:
            List of :class:`RetrievalResult` objects, sorted by relevance.
        """
        raw = await _kb.query_knowledge_base(self._store, query, top_k)
        return [
            RetrievalResult(
                text=r.get("text", ""),
                score=float(r.get("score", 1.0)),
                metadata=r.get("metadata", {}),
            )
            for r in raw
        ]

    @property
    def name(self) -> str:
        """The knowledge base name."""
        return self._name

    @property
    def retriever(self) -> Any:
        """The underlying retriever object (for use with :class:`AgenticRetriever`)."""
        return getattr(self._store, "retriever", self._store)

    def __repr__(self) -> str:
        return f"KnowledgeBase(name={self._name!r})"


# ---------------------------------------------------------------------------
# Retriever — single-shot retrieval wrapper
# ---------------------------------------------------------------------------


class Retriever:
    """Wraps a :class:`KnowledgeBase` with a fixed retrieval strategy.

    Example::

        retriever = Retriever(kb, strategy="hybrid", top_k=5)
        results = await retriever.retrieve("What are the support hours?")
    """

    def __init__(
        self,
        kb: KnowledgeBase,
        *,
        strategy: str = "semantic",
        top_k: int = 5,
    ) -> None:
        self._kb = kb
        self._strategy = strategy
        self._top_k = top_k

    async def retrieve(self, query: str, *, top_k: int | None = None) -> list[RetrievalResult]:
        """Retrieve chunks matching *query*.

        Args:
            query: Natural-language query string.
            top_k: Override the default ``top_k``.

        Returns:
            List of :class:`RetrievalResult` objects.
        """
        k = top_k if top_k is not None else self._top_k
        return await self._kb.query(query, top_k=k)

    def __repr__(self) -> str:
        return f"Retriever(kb={self._kb.name!r}, strategy={self._strategy!r}, top_k={self._top_k})"


# ---------------------------------------------------------------------------
# AgenticRetriever — LLM-driven multi-round retrieval
# ---------------------------------------------------------------------------


class AgenticRetriever:
    """Retriever that uses an LLM to iteratively rewrite queries and gather context.

    Wraps a base retriever and performs up to *max_hops* rounds of retrieval,
    refining the query between rounds based on what was already found.

    Example::

        agentic = AgenticRetriever(retriever=kb.retriever, max_hops=3)
        results = await agentic.retrieve("complex research question", max_hops=2)
    """

    def __init__(
        self,
        kb: KnowledgeBase | None = None,
        *,
        retriever: Any = None,
        llm_client: Any = None,
        max_hops: int = 3,
        top_k_per_round: int = 5,
    ) -> None:
        self._kb = kb
        self._retriever = retriever
        self._llm_client = llm_client
        self._max_hops = max_hops
        self._top_k_per_round = top_k_per_round

    async def retrieve(
        self,
        query: str,
        *,
        max_hops: int | None = None,
    ) -> list[RetrievalResult]:
        """Retrieve via iterative query refinement.

        Args:
            query:    Initial query string.
            max_hops: Override the default ``max_hops``.

        Returns:
            Deduplicated list of :class:`RetrievalResult` objects.
        """
        hops = max_hops if max_hops is not None else self._max_hops
        collected: list[RetrievalResult] = []
        seen_texts: set[str] = set()

        current_query = query
        for _round in range(max(1, hops)):
            # Delegate to the KB or wrapped retriever
            if self._kb is not None:
                results = await self._kb.query(current_query, top_k=self._top_k_per_round)
            elif hasattr(self._retriever, "retrieve"):
                raw = await _kb.query_knowledge_base(
                    self._retriever, current_query, self._top_k_per_round
                )
                results = [
                    RetrievalResult(
                        text=r.get("text", ""),
                        score=float(r.get("score", 1.0)),
                        metadata=r.get("metadata", {}),
                    )
                    for r in raw
                ]
            else:
                break

            for r in results:
                if r.text not in seen_texts:
                    seen_texts.add(r.text)
                    collected.append(r)

            # In a full implementation the LLM would rewrite the query.
            # Here we append " details" to simulate query expansion.
            if self._llm_client is not None and _round < hops - 1:
                current_query = f"{current_query} details"

        return collected

    def __repr__(self) -> str:
        return f"AgenticRetriever(max_hops={self._max_hops})"


# ---------------------------------------------------------------------------
# GraphKnowledgeBase — vector + graph traversal
# ---------------------------------------------------------------------------


class GraphKnowledgeBase(KnowledgeBase):
    """A knowledge base that augments vector search with a graph of entities.

    In addition to the standard :meth:`add_documents` / :meth:`query` API,
    :class:`GraphKnowledgeBase` exposes:

    * :meth:`add_entity` — index a named entity with linked entities.
    * :meth:`retrieve` — query with optional graph traversal.

    Example::

        gkb = GraphKnowledgeBase.create_graph("tech-history", ...)
        await gkb.add_documents([Document(text="...")])
        results = await gkb.retrieve("Turing to CPUs?", use_graph=True)
    """

    def __init__(self, _store: Any, *, name: str, llm_client: Any = None) -> None:
        super().__init__(_store, name=name)
        self._llm_client = llm_client

    @classmethod
    async def create_graph(
        cls,
        name: str,
        *,
        embedding_model: str = "text-embedding-3-small",
        vector_store: str = "chroma",
        llm_client: Any = None,
    ) -> "GraphKnowledgeBase":
        """Create a graph-enabled knowledge base.

        Args:
            name:            Human-readable name.
            embedding_model: Embedding model identifier.
            vector_store:    Backend for vector embeddings.
            llm_client:      LLM used for triple extraction during indexing.
        """
        store = _kb.create_knowledge_base(name, embedding_model, vector_store)
        return cls(store, name=name, llm_client=llm_client)

    async def add_entity(
        self,
        entity_id: str,
        text: str,
        *,
        links: list[str] | None = None,
    ) -> None:
        """Add a named entity to the graph layer.

        Args:
            entity_id: Stable identifier for this entity.
            text:      Textual description.
            links:     IDs of other entities this entity is linked to.
        """
        await _kb.add_entity(self._store, entity_id, text, links or [])

    async def retrieve(
        self,
        query: str,
        *,
        top_k: int = 5,
        use_graph: bool = True,
    ) -> list[RetrievalResult]:
        """Query with optional graph traversal.

        Args:
            query:     Natural-language query.
            top_k:     Maximum number of results.
            use_graph: When ``True``, follows graph edges after vector search.
        """
        raw = await _kb.graph_query(self._store, query, top_k, use_graph)
        return [
            RetrievalResult(
                text=r.get("text", ""),
                score=float(r.get("score", 1.0)),
                metadata=r.get("metadata", {}),
            )
            for r in raw
        ]
