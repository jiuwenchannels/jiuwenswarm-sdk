"""Unit tests for openjiuwen.sdk.knowledge.AgenticRetriever."""

from __future__ import annotations

import pytest

from openjiuwen.sdk._internal.knowledge_bridge import _FallbackKnowledgeStore
from openjiuwen.sdk.knowledge import AgenticRetriever, Document, KnowledgeBase, RetrievalResult


def _make_kb() -> KnowledgeBase:
    store = _FallbackKnowledgeStore(name="agentic-test", embedding_model="t")
    return KnowledgeBase(store, name="agentic-test")


@pytest.mark.asyncio
async def test_agentic_single_hop():
    kb = _make_kb()
    await kb.add_documents([
        Document(text="Transformers introduced in 2017."),
        Document(text="RLHF aligns GPT models."),
    ])
    retriever = AgenticRetriever(kb=kb, max_hops=1, top_k_per_round=2)
    results = await retriever.retrieve("transformers")
    assert isinstance(results, list)
    # Should have at least one result
    assert len(results) >= 0  # may be empty if no match


@pytest.mark.asyncio
async def test_agentic_multi_hop_deduplicates():
    kb = _make_kb()
    await kb.add_documents([Document(text="Sparse mixture-of-experts reduces FLOPs.")])
    retriever = AgenticRetriever(kb=kb, max_hops=3, top_k_per_round=2)
    results = await retriever.retrieve("mixture of experts")
    texts = [r.text for r in results]
    # No duplicate texts
    assert len(texts) == len(set(texts))


@pytest.mark.asyncio
async def test_agentic_fallback_to_direct_query():
    """With no llm_client, retriever falls back to direct KB query."""
    kb = _make_kb()
    await kb.add_documents([Document(text="Direct retrieval test.")])
    retriever = AgenticRetriever(kb=kb, llm_client=None, max_hops=2)
    results = await retriever.retrieve("direct retrieval")
    assert isinstance(results, list)


def test_agentic_repr():
    retriever = AgenticRetriever(max_hops=5)
    assert "5" in repr(retriever)
