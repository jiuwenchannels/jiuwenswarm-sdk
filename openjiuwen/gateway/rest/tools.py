"""Tool discovery REST route.

Routes
------
``GET /v1/tools`` — list all tools registered with any agent.

Response::

    {
      "tools": [
        {
          "name": "search_web",
          "description": "Search the web for information.",
          "schema": {"type": "object", "properties": {"query": {"type": "string"}}}
        }
      ]
    }
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/tools")
async def list_tools(request: Request) -> dict[str, Any]:
    """Return all tools registered across all agents."""
    registry = request.state.registry
    seen: dict[str, dict[str, Any]] = {}

    for spec in registry.list_specs():
        for tool in spec.tools:
            if tool.name not in seen:
                seen[tool.name] = {
                    "name": tool.name,
                    "description": getattr(tool, "description", ""),
                    "schema": getattr(tool, "schema", {}),
                }

    return {"tools": list(seen.values())}
