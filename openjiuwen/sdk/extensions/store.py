"""Abstract session store interface for custom backends.

Implement :class:`BaseSessionStore` to plug in your own session storage
(PostgreSQL, DynamoDB, Redis, …).

Example::

    from openjiuwen.sdk.extensions.store import BaseSessionStore, SessionRecord
    from openjiuwen.sdk.extensions import register_store

    class PostgresSessionStore(BaseSessionStore):
        async def save(self, record: SessionRecord) -> None: ...
        async def load(self, session_id: str) -> SessionRecord | None: ...
        async def list(self) -> list[SessionRecord]: ...
        async def delete(self, session_id: str) -> None: ...

    register_store("postgres", PostgresSessionStore(dsn="postgresql://..."))
"""

from __future__ import annotations

import abc
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SessionRecord:
    """A session record as seen by the extension layer.

    Attributes:
        id:         Session ID (unique string).
        title:      Human-readable title.
        mode:       Session mode (``"default"``, etc.).
        created_at: Unix timestamp of creation.
        messages:   Ordered list of message dicts.
        metadata:   Arbitrary extra fields.
    """

    id: str
    title: str = ""
    mode: str = "default"
    created_at: float = 0.0
    messages: list[dict[str, str]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseSessionStore(abc.ABC):
    """Abstract interface for custom session backends.

    Subclass and implement all abstract methods, then register with::

        from openjiuwen.sdk.extensions import register_store
        register_store("my-store", MySessionStore(...))
    """

    @abc.abstractmethod
    async def save(self, record: SessionRecord) -> None:
        """Persist *record* (create or update)."""

    @abc.abstractmethod
    async def load(self, session_id: str) -> SessionRecord | None:
        """Return the record for *session_id*, or ``None`` if not found."""

    @abc.abstractmethod
    async def list(self) -> list[SessionRecord]:
        """Return all stored session records."""

    @abc.abstractmethod
    async def delete(self, session_id: str) -> None:
        """Delete *session_id* (no-op if not found)."""
