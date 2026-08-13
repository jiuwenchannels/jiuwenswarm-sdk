"""Knowledge-base management REST routes.

Routes
------
``POST /v1/knowledge``                          — create a knowledge base.
``POST /v1/knowledge/{name}/documents``         — add documents to a KB.
``POST /v1/knowledge/{name}/query``             — semantic query against a KB.

Create request::

    {"name": "product-docs", "type": "vector"}

Add-documents request::

    {
      "documents": [
        {"content": "Product X does ...", "metadata": {"source": "manual.pdf"}}
      ]
    }

Query request::

    {"query": "How do I reset my password?", "top_k": 5}

Query response::

    {
      "results": [
        {"content": "...", "score": 0.92, "metadata": {...}}
      ]
    }
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()

# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class CreateKBRequest(BaseModel):
    name: str
    type: str = "vector"


class AddDocumentsRequest(BaseModel):
    documents: list[dict[str, Any]]


class QueryRequest(BaseModel):
    query: str
    top_k: int = 5


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/knowledge", status_code=201)
async def create_knowledge_base(body: CreateKBRequest, request: Request) -> dict[str, Any]:
    """Create a new named knowledge base."""
    kb_store = request.state.knowledge_bases
    if body.name in kb_store:
        raise HTTPException(status_code=409, detail=f"Knowledge base {body.name!r} already exists")
    kb_store[body.name] = {"name": body.name, "type": body.type, "document_count": 0}
    return {"knowledge_base": kb_store[body.name]}


@router.post("/knowledge/{name}/documents", status_code=201)
async def add_documents(name: str, body: AddDocumentsRequest, request: Request) -> dict[str, Any]:
    """Add documents to an existing knowledge base."""
    kb_store = request.state.knowledge_bases
    if name not in kb_store:
        raise HTTPException(status_code=404, detail=f"Knowledge base {name!r} not found")

    from openjiuwen.sdk._internal import knowledge_bridge as _kb

    count = 0
    for doc in body.documents:
        await _kb.add_document(
            name,
            content=doc.get("content", ""),
            metadata=doc.get("metadata", {}),
        )
        count += 1

    kb_store[name]["document_count"] = kb_store[name]["document_count"] + count
    return {"added": count, "knowledge_base": name}


@router.post("/knowledge/{name}/query")
async def query_knowledge_base(name: str, body: QueryRequest, request: Request) -> dict[str, Any]:
    """Perform a semantic query against a knowledge base."""
    kb_store = request.state.knowledge_bases
    if name not in kb_store:
        raise HTTPException(status_code=404, detail=f"Knowledge base {name!r} not found")

    from openjiuwen.sdk._internal import knowledge_bridge as _kb

    results = await _kb.query(name, query=body.query, top_k=body.top_k)
    return {
        "results": [
            {
                "content": r.content if hasattr(r, "content") else str(r),
                "score": getattr(r, "score", 0.0),
                "metadata": getattr(r, "metadata", {}),
            }
            for r in results
        ]
    }
