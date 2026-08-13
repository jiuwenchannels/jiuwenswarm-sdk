"""WebSocket envelope dispatcher.

:func:`dispatch` processes one parsed envelope and sends appropriate
response envelopes back over the WebSocket.

Connection state (``client_type``, ``active_session_id``) is maintained in
the :class:`ConnectionState` dataclass that is created per-connection in
:mod:`openjiuwen.gateway.ws.router`.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from openjiuwen.gateway.ws.envelope import (
    make_ack,
    make_done,
    make_error,
    make_token,
    serialise,
)

if TYPE_CHECKING:
    from fastapi import WebSocket

    from openjiuwen.gateway._registry import AgentRegistry, SessionStore

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-connection state
# ---------------------------------------------------------------------------


@dataclass
class ConnectionState:
    """Mutable state kept for the lifetime of one WebSocket connection."""

    client_type: str = "unknown"
    active_session_id: Optional[str] = None
    extra: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


async def dispatch(
    websocket: "WebSocket",
    envelope: dict[str, Any],
    *,
    state: ConnectionState,
    registry: "AgentRegistry",
    sessions: "SessionStore",
    auth_token: Optional[str],
) -> None:
    """Handle one inbound envelope and write response(s) to *websocket*.

    Args:
        websocket:  Open FastAPI WebSocket connection.
        envelope:   Parsed inbound envelope dict (has ``"type"`` key).
        state:      Mutable per-connection state.
        registry:   Gateway agent registry.
        sessions:   Gateway session store.
        auth_token: Server auth token (``None`` → dev mode).
    """
    env_type: str = envelope.get("type", "")

    try:
        if env_type == "connect":
            await _handle_connect(websocket, envelope, state=state, auth_token=auth_token)

        elif env_type == "sessions":
            await _handle_sessions(websocket, sessions=sessions)

        elif env_type == "create_session":
            await _handle_create_session(
                websocket, envelope, state=state, registry=registry, sessions=sessions
            )

        elif env_type == "chat":
            await _handle_chat(
                websocket, envelope, state=state, registry=registry, sessions=sessions
            )

        else:
            log.debug("[ws/dispatcher] unknown envelope type: %r", env_type)
            await websocket.send_text(serialise(make_error(f"Unknown envelope type: {env_type!r}")))

    except Exception as exc:  # noqa: BLE001
        log.exception("[ws/dispatcher] unhandled error for envelope %r", env_type)
        try:
            await websocket.send_text(serialise(make_error(str(exc))))
        except Exception:  # noqa: BLE001
            pass  # connection may already be closing


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


async def _handle_connect(
    websocket: "WebSocket",
    envelope: dict[str, Any],
    *,
    state: ConnectionState,
    auth_token: Optional[str],
) -> None:
    """Process a ``connect`` envelope.

    Optionally validates the bearer token (passed as ``token`` inside the
    envelope payload — used when the HTTP upgrade request cannot carry the
    ``Authorization`` header, e.g. browser WebSocket API).
    """
    # Token check (optional — header-based auth may have already passed)
    if auth_token is not None:
        provided = envelope.get("token", "")
        if provided != auth_token:
            await websocket.send_text(serialise(make_error("Unauthorized")))
            await websocket.close(code=4001)
            return

    client_type: str = envelope.get("client_type", "unknown")
    state.client_type = client_type
    log.debug("[ws/dispatcher] connect from client_type=%r", client_type)

    await websocket.send_text(
        serialise(make_ack(client_type=client_type))
    )


async def _handle_sessions(
    websocket: "WebSocket",
    *,
    sessions: "SessionStore",
) -> None:
    """Return the full session list."""
    all_sessions = sessions.list_all()
    payload = {
        "type": "sessions",
        "sessions": [s.to_dict() for s in all_sessions],
    }
    await websocket.send_text(json.dumps(payload))


async def _handle_create_session(
    websocket: "WebSocket",
    envelope: dict[str, Any],
    *,
    state: ConnectionState,
    registry: "AgentRegistry",
    sessions: "SessionStore",
) -> None:
    """Create a new session and confirm."""
    agent_id: str = envelope.get("agent_id", "")
    title: str = envelope.get("title", "New session")
    mode: str = envelope.get("mode", "default")

    if not registry.has(agent_id):
        await websocket.send_text(
            serialise(make_error(f"Unknown agent: {agent_id!r}"))
        )
        return

    session = await sessions.create(title=title, agent_id=agent_id, mode=mode)
    state.active_session_id = session.id

    payload = {"type": "session_created", "session": session.to_dict()}
    await websocket.send_text(json.dumps(payload))


async def _handle_chat(
    websocket: "WebSocket",
    envelope: dict[str, Any],
    *,
    state: ConnectionState,
    registry: "AgentRegistry",
    sessions: "SessionStore",
) -> None:
    """Run the agent and stream tokens back."""
    session_id: Optional[str] = envelope.get("session_id") or state.active_session_id
    message: str = envelope.get("message", "")

    # Resolve session and agent
    if session_id is None:
        await websocket.send_text(serialise(make_error("No active session. Send create_session first.")))
        return

    session = sessions.get(session_id)
    if session is None:
        await websocket.send_text(serialise(make_error(f"Session {session_id!r} not found")))
        return

    if not registry.has(session.agent_id):
        await websocket.send_text(serialise(make_error(f"Agent {session.agent_id!r} not found")))
        return

    try:
        agent = await registry.get_or_create(session.agent_id)
    except Exception as exc:
        await websocket.send_text(serialise(make_error(str(exc))))
        return

    # Send ack to confirm message received
    await websocket.send_text(serialise(make_ack(session_id=session_id)))

    # Stream tokens
    try:
        async for token in agent.stream(message, session_id=session_id):
            await websocket.send_text(serialise(make_token(token)))
    except Exception as exc:
        await websocket.send_text(serialise(make_error(str(exc))))
        return

    await websocket.send_text(serialise(make_done(session_id=session_id)))
