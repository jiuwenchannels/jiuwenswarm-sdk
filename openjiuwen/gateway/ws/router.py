"""WebSocket route — ``/v1/ws``.

Every client (browser extension, mobile app, SDK remote mode) connects here
and exchanges JSON envelopes for the lifetime of the connection.

Protocol summary
----------------
1. Client connects and may send ``{"type": "connect", "client_type": "browser"}``.
2. Server replies ``{"type": "ack", "protocol_version": "1"}``.
3. Client exchanges ``sessions``, ``create_session``, and ``chat`` envelopes.
4. Server streams ``token`` envelopes and closes each exchange with ``done``.

See :mod:`openjiuwen.gateway.ws.envelope` for the full envelope schema and
:mod:`openjiuwen.gateway.ws.dispatcher` for per-type handling logic.
"""

from __future__ import annotations
from typing import Optional

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from openjiuwen.gateway.ws.dispatcher import ConnectionState, dispatch
from openjiuwen.gateway.ws.envelope import ProtocolError, make_error, parse_envelope, serialise

log = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws")
async def ws_endpoint(websocket: WebSocket) -> None:
    """Accept a WebSocket connection and process envelopes until disconnect."""
    await websocket.accept()

    # Pull shared state from the app
    registry = websocket.app.state.registry
    sessions = websocket.app.state.sessions
    auth_token: Optional[str] = websocket.app.state.auth_token

    state = ConnectionState()
    log.debug("[ws/router] new connection accepted")

    try:
        async for raw in websocket.iter_text():
            try:
                envelope = parse_envelope(raw)
            except ProtocolError as exc:
                await websocket.send_text(serialise(make_error(str(exc))))
                continue

            await dispatch(
                websocket,
                envelope,
                state=state,
                registry=registry,
                sessions=sessions,
                auth_token=auth_token,
            )

    except WebSocketDisconnect:
        log.debug("[ws/router] client disconnected (client_type=%r)", state.client_type)
    except Exception as exc:  # noqa: BLE001
        log.exception("[ws/router] unhandled exception in ws_endpoint")
        try:
            await websocket.send_text(serialise(make_error(str(exc))))
        except Exception:  # noqa: BLE001
            pass
