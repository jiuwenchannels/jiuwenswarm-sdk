"""WebSocket envelope parser and validator.

The JiuwenSwarm WebSocket protocol exchanges JSON envelopes over a single
persistent connection.  Every envelope **must** have a ``"type"`` string field.

Inbound envelope types (client → server)
-----------------------------------------
``connect``        — open the logical connection (carries ``client_type``).
``sessions``       — request the session list.
``create_session`` — create a new session.
``chat``           — send a chat message to an agent.

Outbound envelope types (server → client)
------------------------------------------
``ack``            — handshake confirmation (includes ``protocol_version: "1"``).
``sessions``       — session list response.
``session_created``— new session was created.
``token``          — one streamed text token.
``done``           — agent run completed.
``error``          — a server-side error occurred.

Usage::

    from openjiuwen.gateway.ws.envelope import parse_envelope, ProtocolError

    env = parse_envelope(raw_json_string)
    # env["type"] is guaranteed to be present
"""

from __future__ import annotations

import json
from typing import Any, Optional


class ProtocolError(ValueError):
    """Raised when an envelope cannot be parsed or is structurally invalid."""


def parse_envelope(raw: str) -> dict[str, Any]:
    """Parse a raw JSON string into an envelope dict.

    Args:
        raw: JSON text received from the WebSocket client.

    Returns:
        A dict with at least a ``"type"`` key.

    Raises:
        :class:`ProtocolError` if the JSON is malformed or ``"type"`` is missing.
    """
    try:
        env = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ProtocolError(f"Malformed JSON envelope: {exc}") from exc

    if not isinstance(env, dict):
        raise ProtocolError(f"Envelope must be a JSON object, got {type(env).__name__}")

    if "type" not in env:
        raise ProtocolError("Envelope missing required field 'type'")

    env_type = env["type"]
    if not isinstance(env_type, str) or not env_type:
        raise ProtocolError(f"Envelope 'type' must be a non-empty string, got {env_type!r}")

    return env


def make_ack(*, session_id: Optional[str] = None, client_type: Optional[str] = None) -> dict[str, Any]:
    """Build a server ``ack`` envelope."""
    env: dict[str, Any] = {"type": "ack", "protocol_version": "1"}
    if session_id is not None:
        env["session_id"] = session_id
    if client_type is not None:
        env["client_type"] = client_type
    return env


def make_token(text: str) -> dict[str, Any]:
    return {"type": "token", "text": text}


def make_done(session_id: Optional[str] = None) -> dict[str, Any]:
    env: dict[str, Any] = {"type": "done"}
    if session_id is not None:
        env["session_id"] = session_id
    return env


def make_error(message: str) -> dict[str, Any]:
    return {"type": "error", "message": message}


def serialise(env: dict[str, Any]) -> str:
    return json.dumps(env)
