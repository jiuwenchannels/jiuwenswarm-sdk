"""SDK Permission Engine façade — fine-grained tool permission enforcement.

Define which tools an agent is allowed to call, which require approval, and
which are always denied.

Quick start::

    from openjiuwen.sdk.control.permissions import PermissionEngine, PermissionRule

    engine = PermissionEngine(rules=[
        PermissionRule(tool="file_delete", level="deny"),
        PermissionRule(tool="shell", level="ask"),
    ])

    agent = await Agent.create("guarded", permission_engine=engine, ...)
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import Any

from openjiuwen.sdk._internal import permission_bridge as _pb


# ---------------------------------------------------------------------------
# Permission level
# ---------------------------------------------------------------------------


class PermissionLevel(str, enum.Enum):
    """Controls what happens when an agent tries to use a tool."""

    ALLOW = "allow"   #: Execute without prompting.
    ASK = "ask"       #: Pause and wait for user approval.
    DENY = "deny"     #: Reject the tool call immediately.


# ---------------------------------------------------------------------------
# PermissionRule
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PermissionRule:
    """A single permission rule.

    Attributes:
        tool:    Tool name this rule applies to (use ``"*"`` for all tools).
        agent:   Agent name this rule applies to (use ``"*"`` for all agents).
        level:   :class:`PermissionLevel` (``allow`` / ``ask`` / ``deny``).
        scope:   Use ``"default"`` for the catch-all default rule.
    """

    tool: str = "*"
    agent: str = "*"
    level: PermissionLevel = PermissionLevel.ALLOW
    scope: str = "tool"  # "tool" | "agent" | "default"

    def to_dict(self) -> dict[str, str]:
        return {"tool": self.tool, "agent": self.agent, "level": self.level.value, "scope": self.scope}


# ---------------------------------------------------------------------------
# PermissionEngine façade
# ---------------------------------------------------------------------------


class PermissionEngine:
    """Enforces a list of :class:`PermissionRule` objects on tool calls.

    Pass to :meth:`~openjiuwen.sdk.core.agent.Agent.create` as ``permission_engine=``.

    Example::

        engine = PermissionEngine(rules=[
            PermissionRule(tool="file_delete", level=PermissionLevel.DENY),
            PermissionRule(tool="shell", level=PermissionLevel.ASK),
        ])
        allowed = engine.check("my-agent", "read_file")  # True
        allowed = engine.check("my-agent", "file_delete")  # False
    """

    def __init__(
        self,
        rules: list[PermissionRule] | None = None,
        *,
        default_level: PermissionLevel = PermissionLevel.ALLOW,
    ) -> None:
        self._rules = list(rules or [])
        self._default_level = default_level
        # Build the underlying engine
        rule_dicts = [r.to_dict() for r in self._rules]
        rule_dicts.append({"scope": "default", "level": default_level.value})
        self._engine: Any = _pb.create_permission_engine(rule_dicts)

    def check(self, agent_id: str, tool_name: str) -> bool:
        """Return ``True`` if *agent_id* is allowed to use *tool_name*.

        Args:
            agent_id:  The agent's identifier.
            tool_name: The tool being checked.

        Returns:
            ``True`` if the :class:`PermissionLevel` is :attr:`PermissionLevel.ALLOW`;
            ``False`` for :attr:`PermissionLevel.DENY` or :attr:`PermissionLevel.ASK`.
        """
        return _pb.check_permission(self._engine, agent_id, tool_name)

    def allow(self, agent_id: str, tool_name: str) -> bool:
        """Alias for :meth:`check`."""
        return self.check(agent_id, tool_name)

    def add_rule(self, rule: PermissionRule) -> None:
        """Add a rule at runtime (takes effect immediately).

        Args:
            rule: :class:`PermissionRule` to add.
        """
        self._rules.append(rule)
        # Rebuild the underlying engine
        rule_dicts = [r.to_dict() for r in self._rules]
        rule_dicts.append({"scope": "default", "level": self._default_level.value})
        self._engine = _pb.create_permission_engine(rule_dicts)

    @property
    def rules(self) -> list[PermissionRule]:
        """The current list of permission rules."""
        return list(self._rules)

    @property
    def config(self) -> Any:
        """The underlying runtime permission config object (or ``None``)."""
        return getattr(self._engine, "config", None)

    @property
    def _host(self) -> Any:
        return getattr(self._engine, "_host", None)

    def __repr__(self) -> str:
        return f"PermissionEngine(rules={len(self._rules)}, default={self._default_level.value!r})"
