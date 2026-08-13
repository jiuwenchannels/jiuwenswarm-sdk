"""Unit tests for openjiuwen.sdk.knowledge — KnowledgeBase façade.

Tests use the in-process fallback store (no runtime needed).
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from openjiuwen.sdk._internal.knowledge_bridge import _FallbackKnowledgeStore
from openjiuwen.sdk.knowledge import Document, KnowledgeBase, RetrievalResult, Retriever


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_store() -> _FallbackKnowledgeStore:
    return _FallbackKnowledgeStore(name="test-kb", embedding_model="text-embedding-3-small")


def _make_kb(name: str = "test-kb") -> KnowledgeBase:
    store = _make_store()
    with patch(
        "openjiuwen.sdk._internal.knowledge_bridge.create_knowledge_base",
        return_value=store,
    ):
        return KnowledgeBase(store, name=name)


# ---------------------------------------------------------------------------
# KnowledgeBase tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_knowledge_base_create():
    store = _make_store()
    with patch(
        "openjiuwen.sdk._internal.knowledge_bridge.create_knowledge_base",
        return_value=store,
    ):
        kb = await KnowledgeBase.create("my-kb", embedding_model="text-embedding-3-small")
    assert kb.name == "my-kb"


@pytest.mark.asyncio
async def test_knowledge_base_add_and_query():
    kb = _make_kb()
    docs = [
        Document(text="Refunds are valid within 30 days."),
        Document(text="Support available Monday–Friday."),
    ]
    await kb.add_documents(docs)
    results = await kb.query("refund policy", top_k=1)
    assert len(results) >= 1
    assert isinstance(results[0], RetrievalResult)
    assert "Refund" in results[0].text or "refund" in results[0].text.lower()


@pytest.mark.asyncio
async def test_knowledge_base_query_top_k():
    kb = _make_kb()
    docs = [Document(text=f"Document number {i}.") for i in range(10)]
    await kb.add_documents(docs)
    results = await kb.query("document", top_k=3)
    assert len(results) <= 3


def test_knowledge_base_repr():
    kb = _make_kb("repr-test")
    assert "repr-test" in repr(kb)


def test_document_defaults():
    doc = Document(text="Hello world.")
    assert doc.text == "Hello world."
    assert doc.metadata == {}
    assert doc.id is None


# ---------------------------------------------------------------------------
# Retriever tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retriever_retrieve():
    kb = _make_kb()
    await kb.add_documents([Document(text="The cat sat on the mat.")])
    retriever = Retriever(kb, strategy="semantic", top_k=2)
    results = await retriever.retrieve("cat mat")
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_retriever_override_top_k():
    kb = _make_kb()
    docs = [Document(text=f"Doc {i}") for i in range(8)]
    await kb.add_documents(docs)
    retriever = Retriever(kb, top_k=10)
    results = await retriever.retrieve("doc", top_k=2)
    assert len(results) <= 2


def test_retriever_repr():
    kb = _make_kb()
    r = Retriever(kb, strategy="hybrid", top_k=5)
    assert "hybrid" in repr(r)
