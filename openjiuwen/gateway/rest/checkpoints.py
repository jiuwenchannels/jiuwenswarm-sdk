"""Checkpoint management REST routes.

Routes
------
``POST /v1/agents/{agent_id}/checkpoint``  — save a checkpoint for a running agent.
``GET  /v1/checkpoints``                   — list all checkpoints.
``POST /v1/checkpoints/{checkpoint_id}/restore`` — restore an agent from a checkpoint.

Checkpoint response::

    {
      "checkpoint": {
        "id": "ckpt_abc123",
        "agent_id": "researcher",
        "created_at": "2024-01-01T00:00:00+00:00"
      }
    }
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request

router = APIRouter()


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("/agents/{agent_id}/checkpoint", status_code=201)
async def save_checkpoint(agent_id: str, request: Request) -> dict[str, Any]:
    """Save the current state of a running agent as a checkpoint."""
    registry = request.state.registry
    checkpoints = request.state.checkpoints

    if not registry.has(agent_id):
        raise HTTPException(status_code=404, detail=f"Agent {agent_id!r} not found")

    try:
        agent = await registry.get_or_create(agent_id)
        checkpoint_id = await agent.checkpoint()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    entry = await checkpoints.save(agent_id=agent_id, checkpoint_id=checkpoint_id)
    return {"checkpoint": entry.to_dict()}


@router.get("/checkpoints")
async def list_checkpoints(request: Request) -> dict[str, Any]:
    """Return all saved checkpoints."""
    checkpoints = request.state.checkpoints
    return {"checkpoints": [e.to_dict() for e in checkpoints.list_all()]}


@router.post("/checkpoints/{checkpoint_id}/restore", status_code=201)
async def restore_checkpoint(checkpoint_id: str, request: Request) -> dict[str, Any]:
    """Restore an agent from a previously saved checkpoint."""
    checkpoints = request.state.checkpoints
    entry = checkpoints.get(checkpoint_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Checkpoint {checkpoint_id!r} not found")

    from openjiuwen.sdk.core.agent import Agent

    try:
        agent = await Agent.restore(checkpoint_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    # Register the restored agent under the same id
    registry = request.state.registry
    registry._instances[entry.agent_id] = agent  # noqa: SLF001  — intentional internal access

    return {
        "restored": True,
        "agent_id": entry.agent_id,
        "checkpoint_id": checkpoint_id,
    }
