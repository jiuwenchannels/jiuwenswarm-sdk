"""Agent management REST routes.

Routes
------
``GET  /v1/agents``             — list all registered agents.
``GET  /v1/agents/{agent_id}``  — describe a single agent.
``POST /v1/agents/{agent_id}/run``    — blocking agent run.
``POST /v1/agents/{agent_id}/stream`` — SSE streaming agent run.

Request body for ``/run`` and ``/stream``::

    {"prompt": "What is 2+2?", "session_id": null}

SSE stream format::

    event: token
    data: {"text": "4"}

    event: done
    data: {"session_id": "sess_abc123", "metadata": {}}
"""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()

PROTOCOL_VERSION = "1"


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class RunRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_registry(request: Request):
    return request.state.registry


def _get_sessions(request: Request):
    return request.state.sessions


async def _sse_stream(chunks: AsyncIterator[str], session_id: str) -> AsyncIterator[str]:
    async for token in chunks:
        yield f"event: token\ndata: {json.dumps({'text': token})}\n\n"
    yield f"event: done\ndata: {json.dumps({'session_id': session_id, 'metadata': {}})}\n\n"


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/agents")
async def list_agents(request: Request) -> dict[str, Any]:
    """List all registered agents."""
    registry = _get_registry(request)
    return {"agents": [spec.to_dict() for spec in registry.list_specs()]}


@router.get("/agents/{agent_id}")
async def get_agent(agent_id: str, request: Request) -> dict[str, Any]:
    """Describe a single agent by ID."""
    registry = _get_registry(request)
    spec = registry.get_spec(agent_id)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id!r} not found")
    return {"agent": spec.to_dict()}


@router.post("/agents/{agent_id}/run")
async def run_agent(agent_id: str, body: RunRequest, request: Request) -> dict[str, Any]:
    """Run an agent and return the complete response."""
    registry = _get_registry(request)
    if not registry.has(agent_id):
        raise HTTPException(status_code=404, detail=f"Agent {agent_id!r} not found")

    try:
        agent = await registry.get_or_create(agent_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    result = await agent.run(body.prompt, session_id=body.session_id)
    return {
        "text": result.text,
        "session_id": result.session_id,
        "metadata": result.metadata,
    }


@router.post("/agents/{agent_id}/stream")
async def stream_agent(agent_id: str, body: RunRequest, request: Request) -> StreamingResponse:
    """Stream an agent's response as Server-Sent Events."""
    registry = _get_registry(request)
    if not registry.has(agent_id):
        raise HTTPException(status_code=404, detail=f"Agent {agent_id!r} not found")

    try:
        agent = await registry.get_or_create(agent_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    session_id = body.session_id or f"sess_{agent_id}_stream"

    return StreamingResponse(
        _sse_stream(agent.stream(body.prompt, session_id=body.session_id), session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
