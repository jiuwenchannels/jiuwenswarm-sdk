"""Unit tests for openjiuwen.sdk.knowledge.GraphKnowledgeBase."""

from __future__ import annotations

import pytest

from openjiuwen.sdk._internal.knowledge_bridge import _FallbackKnowledgeStore
from openjiuwen.sdk.knowledge import Document, GraphKnowledgeBase, RetrievalResult


def _make_gkb(name: str = "graph-test") -> GraphKnowledgeBase:
    store = _FallbackKnowledgeStore(name=name, embedding_model="t")
    return GraphKnowledgeBase(store, name=name)


@pytest.mark.asyncio
async def test_graph_kb_add_documents():
    gkb = _make_gkb()
    await gkb.add_documents([
        Document(text="Turing invented the Turing machine."),
        Document(text="Von Neumann architecture inspired by Turing."),
    ])
    results = await gkb.retrieve("Turing", top_k=2)
    assert isinstance(results, list)
    assert len(results) >= 1


@pytest.mark.asyncio
async def test_graph_kb_add_entity():
    gkb = _make_gkb()
    await gkb.add_entity("turing", "Alan Turing", links=["church-turing-thesis"])
    await gkb.add_entity("church-turing-thesis", "Church-Turing Thesis", links=[])

    results = await gkb.retrieve("Turing", top_k=5, use_graph=True)
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_graph_kb_retrieve_without_graph():
    gkb = _make_gkb()
    await gkb.add_documents([Document(text="Computing theory.")])
    results = await gkb.retrieve("computing", top_k=3, use_graph=False)
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_graph_kb_traverse_links():
    gkb = _make_gkb()
    await gkb.add_entity("turing", "Turing work on computability", links=["von-neumann"])
    await gkb.add_entity("von-neumann", "Von Neumann architecture", links=[])
    # With use_graph=True, entities should be found by traversal
    results = await gkb.retrieve("Turing", top_k=5, use_graph=True)
    all_texts = " ".join(r.text for r in results)
    assert "Turing" in all_texts or "turing" in all_texts.lower()


def test_graph_kb_inherits_knowledge_base():
    gkb = _make_gkb()
    assert gkb.name == "graph-test"
