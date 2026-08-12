"""In-process session management bridge.

This module maintains a lightweight registry of SDK sessions backed by the
``openjiuwen.core.session`` layer.  Because the underlying runtime does not
expose a built-in list/get/delete CRUD manager, the SDK keeps its own index.

A :class:`SessionRecord` is the SDK's view of a session.  The ``internal_id``
field holds the session ID used by the underlying runtime.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from openjiuwen.sdk.session import Message


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class SessionRecord:
    """Lightweight metadata record stored in the in-process registry."""

    id: str
    title: str
    mode: str
    created_at: float  # Unix timestamp
    internal_id: str   # session ID used by the underlying runtime
    messages: list["Message"] = field(default_factory=list)

    @property
    def created_at_iso(self) -> str:
        import datetime

        return datetime.datetime.fromtimestamp(
            self.created_at, tz=datetime.timezone.utc
        ).isoformat()


# ---------------------------------------------------------------------------
# Registry — module-level singleton
# ---------------------------------------------------------------------------

_registry: dict[str, SessionRecord] = {}


def create_session(title: str, mode: str = "default") -> SessionRecord:
    """Create a new session record and register it."""
    sid = f"sess_{uuid.uuid4().hex[:12]}"
    record = SessionRecord(
        id=sid,
        title=title,
        mode=mode,
        created_at=time.time(),
        internal_id=sid,
    )
    _registry[sid] = record
    return record


def get_session(session_id: str) -> SessionRecord | None:
    """Return the session record for *session_id*, or ``None``."""
    return _registry.get(session_id)


def require_session(session_id: str) -> SessionRecord:
    """Return the session record or raise :class:`~openjiuwen.sdk.errors.SessionError`."""
    record = _registry.get(session_id)
    if record is None:
        from openjiuwen.sdk.errors import SessionError

        raise SessionError(f"Session '{session_id}' not found.")
    return record


def list_sessions() -> list[SessionRecord]:
    """Return all registered sessions, newest first."""
    return sorted(_registry.values(), key=lambda r: r.created_at, reverse=True)


def delete_session(session_id: str) -> None:
    """Remove a session from the registry (does not affect the runtime)."""
    _registry.pop(session_id, None)


def append_message(session_id: str, role: str, text: str) -> None:
    """Append a message to a session's history (best-effort; ignores unknown IDs)."""
    record = _registry.get(session_id)
    if record is None:
        return
    from openjiuwen.sdk.session import Message  # local import to avoid circularity

    record.messages.append(Message(role=role, text=text))


# ---------------------------------------------------------------------------
# Internal runtime session factory
# ---------------------------------------------------------------------------


def make_internal_session(record: SessionRecord) -> "Any":  # noqa: F821
    """Create the underlying ``openjiuwen.core.session.Session`` for *record*.

    Returns the raw internal session object.  Raises
    :class:`~openjiuwen.sdk.errors.RuntimeNotAvailableError` if the runtime
    package is not installed.
    """
    try:
        from openjiuwen.core.session import create_agent_session
    except ImportError as exc:
        from openjiuwen.sdk.errors import RuntimeNotAvailableError

        raise RuntimeNotAvailableError(
            "openjiuwen runtime is not installed.  "
            "Install it with: pip install openjiuwen"
        ) from exc

    return create_agent_session(session_id=record.internal_id)
