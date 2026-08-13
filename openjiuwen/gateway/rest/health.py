"""GET /v1/health — liveness probe.

Returns a simple JSON object that confirms the gateway is running and reports
the current software version and WebSocket protocol version.

Response::

    {"status": "ok", "version": "1.0.0", "protocol_version": "1"}
"""

from __future__ import annotations
from typing import Optional

from fastapi import APIRouter

router = APIRouter()

# Imported lazily to avoid hard-coding at module level
try:
    from openjiuwen.sdk import __version__ as _SDK_VERSION  # type: ignore[attr-defined]
except Exception:
    _SDK_VERSION = "1.0.0"

PROTOCOL_VERSION = "1"


@router.get("/health")
async def health() -> dict:
    """Return gateway liveness status."""
    return {
        "status": "ok",
        "version": _SDK_VERSION,
        "protocol_version": PROTOCOL_VERSION,
    }
