"""Tests for knowledge base REST routes."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def test_create_knowledge_base(client):
    resp = client.post("/v1/knowledge", json={"name": "docs", "type": "vector"})
    assert resp.status_code == 201
    kb = resp.json()["knowledge_base"]
    assert kb["name"] == "docs"
    assert kb["type"] == "vector"


def test_create_knowledge_base_conflict(client):
    client.post("/v1/knowledge", json={"name": "kb1"})
    resp = client.post("/v1/knowledge", json={"name": "kb1"})
    assert resp.status_code == 409


# ---------------------------------------------------------------------------
# Document add (bridges patched)
# ---------------------------------------------------------------------------


@dataclass
class _FakeResult:
    content: str
    score: float = 0.9
    metadata: dict = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


def test_add_documents(client, monkeypatch):
    client.post("/v1/knowledge", json={"name": "kb2"})

    async def _fake_add(name, *, content, metadata):
        pass

    monkeypatch.setattr(
        "openjiuwen.sdk._internal.knowledge_bridge.add_document",
        _fake_add,
        raising=False,
    )

    resp = client.post(
        "/v1/knowledge/kb2/documents",
        json={"documents": [{"content": "Doc one"}, {"content": "Doc two"}]},
    )
    assert resp.status_code == 201
    assert resp.json()["added"] == 2


def test_add_documents_unknown_kb_404(client):
    resp = client.post(
        "/v1/knowledge/nosuchkb/documents",
        json={"documents": [{"content": "x"}]},
    )
    assert resp.status_code == 404


def test_query_knowledge_base(client, monkeypatch):
    client.post("/v1/knowledge", json={"name": "kb3"})

    async def _fake_query(name, *, query, top_k):
        return [_FakeResult(content="Relevant document", score=0.95)]

    monkeypatch.setattr(
        "openjiuwen.sdk._internal.knowledge_bridge.query",
        _fake_query,
        raising=False,
    )

    resp = client.post(
        "/v1/knowledge/kb3/query",
        json={"query": "something", "top_k": 3},
    )
    assert resp.status_code == 200
    results = resp.json()["results"]
    assert len(results) == 1
    assert results[0]["content"] == "Relevant document"
    assert results[0]["score"] == pytest.approx(0.95)


def test_query_unknown_kb_404(client):
    resp = client.post("/v1/knowledge/nosuchkb/query", json={"query": "x"})
    assert resp.status_code == 404
