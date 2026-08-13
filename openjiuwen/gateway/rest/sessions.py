"""Session management REST routes + chat/stream endpoints.

Routes
------
``GET    /v1/sessions``                      — list sessions.
``POST   /v1/sessions``                      — create a session.
``GET    /v1/sessions/{id}``                 — get a session.
``DELETE /v1/sessions/{id}``                 — delete a session.
``POST   /v1/sessions/{id}/chat``            — blocking chat (returns full response).
``POST   /v1/sessions/{id}/chat/stream``     — SSE streaming chat.

Create request::

    {"title": "My session", "agent_id": "researcher", "mode": "default"}

Chat request::

    {"message": "Hello, what can you do?"}

SSE stream format::

    event: token
    data: {"text": "I can..."}

    event: done
    data: {"session_id": "sess_abc123"}
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class CreateSessionRequest(BaseModel):
    title: str = "New session"
    agent_id: str
    mode: str = "default"


class ChatRequest(BaseModel):
    message: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_sessions(request: Request):
    return request.state.sessions


def _get_registry(request: Request):
    return request.state.registry


async def _sse_chat_stream(chunks: AsyncIterator[str], session_id: str) -> AsyncIterator[str]:
    async for token in chunks:
        yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"
    yield f"event: done\ndata: {json.dumps({'session_id': session_id})}\n\n"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/sessions")
async def list_sessions(request: Request) -> dict[str, Any]:
    """Return all known sessions."""
    store = _get_sessions(request)
    return {"sessions": [s.to_dict() for s in store.list_all()]}


@router.post("/sessions", status_code=201)
async def create_session(body: CreateSessionRequest, request: Request) -> dict[str, Any]:
    """Create a new session tied to an agent."""
    registry = _get_registry(request)
    if not registry.has(body.agent_id):
        raise HTTPException(status_code=404, detail=f"Agent {body.agent_id!r} not found")

    store = _get_sessions(request)
    session = await store.create(title=body.title, agent_id=body.agent_id, mode=body.mode)
    return {"session": session.to_dict()}


@router.get("/sessions/{session_id}")
async def get_session(session_id: str, request: Request) -> dict[str, Any]:
    """Fetch a single session by ID."""
    store = _get_sessions(request)
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    return {"session": session.to_dict()}


@router.delete("/sessions/{session_id}")
async def delete_session(session_id: str, request: Request) -> dict[str, Any]:
    """Delete a session."""
    store = _get_sessions(request)
    deleted = await store.delete(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")
    return {"deleted": True, "id": session_id}


@router.post("/sessions/{session_id}/chat")
async def chat(session_id: str, body: ChatRequest, request: Request) -> dict[str, Any]:
    """Send a message to the session's agent; return the complete response."""
    store = _get_sessions(request)
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    registry = _get_registry(request)
    try:
        agent = await registry.get_or_create(session.agent_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Agent {session.agent_id!r} not found")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    result = await agent.run(body.message, session_id=session_id)
    return {
        "text": result.text,
        "session_id": session_id,
        "metadata": result.metadata,
    }


@router.post("/sessions/{session_id}/chat/stream")
async def chat_stream(session_id: str, body: ChatRequest, request: Request) -> StreamingResponse:
    """Stream the agent's response as Server-Sent Events."""
    store = _get_sessions(request)
    session = store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id!r} not found")

    registry = _get_registry(request)
    try:
        agent = await registry.get_or_create(session.agent_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Agent {session.agent_id!r} not found")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return StreamingResponse(
        _sse_chat_stream(agent.stream(body.message, session_id=session_id), session_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
