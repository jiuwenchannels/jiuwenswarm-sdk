"""In-memory agent registry and session store.

Both classes are used as FastAPI dependency-injected singletons via the
request state attached in :func:`~openjiuwen.gateway.app.build_gateway_app`.

The agent factory (``_agent_factory``) is a module-level callable so that
tests can patch it without touching the real ``Agent.create``::

    import openjiuwen.gateway._registry as reg

    async def _fake_create(name, *, model, tools, system_prompt, **_):
        return FakeAgent()

    monkeypatch.setattr(reg, "_agent_factory", _fake_create)
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from openjiuwen.gateway.config import AgentSpec

if TYPE_CHECKING:
    from openjiuwen.sdk.core.agent import Agent


# ---------------------------------------------------------------------------
# Patchable factory (override in tests)
# ---------------------------------------------------------------------------

async def _agent_factory(
    name: str,
    *,
    model: Any,
    tools: list,
    system_prompt: Optional[str],
    **kwargs: Any,
) -> "Agent":
    """Create an in-process Agent.  Patchable in unit tests."""
    from openjiuwen.sdk.core.agent import Agent

    return await Agent.create(
        name,
        model=model,
        tools=tools,
        system_prompt=system_prompt,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# AgentRegistry
# ---------------------------------------------------------------------------


class AgentRegistry:
    """Thread-safe registry of :class:`~openjiuwen.gateway.config.AgentSpec` objects.

    Agents are created lazily on first request and cached.

    Args:
        specs: Pre-registered agent specs from :class:`~openjiuwen.gateway.config.GatewayConfig`.
    """

    def __init__(self, specs: list[AgentSpec]) -> None:
        self._specs: dict[str, AgentSpec] = {s.id: s for s in specs}
        self._instances: dict[str, "Agent"] = {}
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------
    # Read-only spec access
    # ------------------------------------------------------------------

    def list_specs(self) -> list[AgentSpec]:
        return list(self._specs.values())

    def get_spec(self, agent_id: str) -> AgentSpec | None:
        return self._specs.get(agent_id)

    def has(self, agent_id: str) -> bool:
        return agent_id in self._specs

    # ------------------------------------------------------------------
    # Lazy agent creation
    # ------------------------------------------------------------------

    async def get_or_create(self, agent_id: str) -> "Agent":
        """Return a cached Agent or create one from the registered spec."""
        if agent_id in self._instances:
            return self._instances[agent_id]

        async with self._lock:
            # Double-checked locking
            if agent_id in self._instances:
                return self._instances[agent_id]

            spec = self._specs.get(agent_id)
            if spec is None:
                raise KeyError(f"Unknown agent: {agent_id!r}")

            agent = await _agent_factory(
                spec.name,
                model=spec.model,
                tools=spec.tools,
                system_prompt=spec.system_prompt,
            )
            self._instances[agent_id] = agent

        return self._instances[agent_id]


# ---------------------------------------------------------------------------
# Session data model
# ---------------------------------------------------------------------------


@dataclass
class SessionData:
    """In-memory representation of one conversation session."""

    id: str
    title: str
    agent_id: str
    mode: str = "default"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "agent_id": self.agent_id,
            "mode": self.mode,
            "created_at": self.created_at.isoformat(),
        }


# ---------------------------------------------------------------------------
# SessionStore
# ---------------------------------------------------------------------------


class SessionStore:
    """Thread-safe, in-memory store of :class:`SessionData` objects."""

    def __init__(self) -> None:
        self._sessions: dict[str, SessionData] = {}
        self._lock = asyncio.Lock()

    async def create(
        self,
        title: str,
        agent_id: str,
        mode: str = "default",
    ) -> SessionData:
        sid = f"sess_{uuid.uuid4().hex[:16]}"
        data = SessionData(id=sid, title=title, agent_id=agent_id, mode=mode)
        async with self._lock:
            self._sessions[sid] = data
        return data

    def get(self, session_id: str) -> SessionData | None:
        return self._sessions.get(session_id)

    def list_all(self) -> list[SessionData]:
        return list(self._sessions.values())

    async def delete(self, session_id: str) -> bool:
        async with self._lock:
            return self._sessions.pop(session_id, None) is not None


# ---------------------------------------------------------------------------
# Checkpoint store (simple in-memory; real backends registered via extensions)
# ---------------------------------------------------------------------------


@dataclass
class CheckpointEntry:
    id: str
    agent_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "created_at": self.created_at.isoformat(),
        }


class CheckpointStore:
    """In-memory checkpoint index (maps checkpoint_id → entry)."""

    def __init__(self) -> None:
        self._checkpoints: dict[str, CheckpointEntry] = {}
        self._lock = asyncio.Lock()

    async def save(self, agent_id: str, checkpoint_id: str) -> CheckpointEntry:
        entry = CheckpointEntry(id=checkpoint_id, agent_id=agent_id)
        async with self._lock:
            self._checkpoints[checkpoint_id] = entry
        return entry

    def get(self, checkpoint_id: str) -> CheckpointEntry | None:
        return self._checkpoints.get(checkpoint_id)

    def list_all(self) -> list[CheckpointEntry]:
        return list(self._checkpoints.values())
