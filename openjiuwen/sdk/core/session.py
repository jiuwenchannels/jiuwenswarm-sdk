"""SDK Session façade.

A :class:`Session` represents a persistent conversation context.  Multiple
:class:`~openjiuwen.sdk.core.agent.Agent` calls that share a session ID carry
memory of prior turns.

Usage::

    session = await Session.create(title="Research notes")
    agent = await Agent.create("researcher", model=ModelConfig.from_env())

    await agent.run("What is a transformer?", session_id=session.id)
    await agent.run("Give me a code example.",  session_id=session.id)

    for msg in await session.history():
        print(f"[{msg.role}] {msg.text[:80]}")
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass


# ---------------------------------------------------------------------------
# Message — one turn in a conversation
# ---------------------------------------------------------------------------


@dataclass
class Message:
    """A single message in a session's conversation history.

    Attributes:
        role: ``"user"`` or ``"assistant"``.
        text: The message content.
    """

    role: str
    text: str


# ---------------------------------------------------------------------------
# Session façade
# ---------------------------------------------------------------------------


class Session:
    """A named, persistent conversation context.

    Obtain sessions via :meth:`create`, :meth:`list`, or :meth:`get` — do
    not call the constructor directly.

    Attributes:
        id:         Stable identifier (e.g. ``"sess_abc123"``).
        title:      Human-readable name.
        mode:       Agent mode (``"default"``, ``"deep"``, etc.).
        created_at: Unix timestamp.
    """

    def __init__(self, _record: "Any") -> None:  # noqa: F821
        self._record = _record

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def id(self) -> str:
        return self._record.id

    @property
    def title(self) -> str:
        return self._record.title

    @property
    def mode(self) -> str:
        return self._record.mode

    @property
    def created_at(self) -> float:
        return self._record.created_at

    # ------------------------------------------------------------------
    # Factory / class-level operations
    # ------------------------------------------------------------------

    @classmethod
    async def create(cls, title: str, mode: str = "default") -> "Session":
        """Create a new session.

        Args:
            title: Human-readable session name.
            mode:  Agent mode.  Use ``"default"`` for most cases.

        Returns:
            The newly created :class:`Session`.
        """
        from openjiuwen.sdk._internal.session_bridge import create_session

        record = create_session(title=title, mode=mode)
        return cls(record)

    @classmethod
    async def list(cls) -> list["Session"]:
        """Return all sessions, newest first."""
        from openjiuwen.sdk._internal.session_bridge import list_sessions

        return [cls(r) for r in list_sessions()]

    @classmethod
    async def get(cls, session_id: str) -> "Session":
        """Retrieve a session by ID.

        Raises:
            :class:`~openjiuwen.sdk.core.errors.SessionError`: if not found.
        """
        from openjiuwen.sdk._internal.session_bridge import require_session

        record = require_session(session_id)
        return cls(record)

    # ------------------------------------------------------------------
    # Instance operations
    # ------------------------------------------------------------------

    async def history(self) -> list[Message]:
        """Return the conversation history for this session."""
        return list(self._record.messages)

    async def delete(self) -> None:
        """Remove this session from the local registry."""
        from openjiuwen.sdk._internal.session_bridge import delete_session

        delete_session(self.id)

    # ------------------------------------------------------------------
    # Dunder
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"Session(id={self.id!r}, title={self.title!r})"
