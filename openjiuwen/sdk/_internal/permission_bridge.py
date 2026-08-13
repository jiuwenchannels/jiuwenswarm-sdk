"""Permission engine bridge.

Wraps ``openjiuwen.harness.security`` primitives behind module-level
patchable functions.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Module-level patchable callables
# ---------------------------------------------------------------------------


def create_permission_engine(rules: list[dict[str, Any]]) -> Any:
    """Create a permission engine via the runtime (patchable)."""
    try:
        from openjiuwen.harness.security import PermissionEngine, PermissionsSection, PermissionLevel

        overrides: dict[str, Any] = {}
        default = PermissionLevel.ALLOW
        for rule in rules:
            if rule.get("scope") == "default":
                level_str = rule.get("level", "allow").upper()
                default = getattr(PermissionLevel, level_str, PermissionLevel.ALLOW)
            else:
                tool_name = rule.get("tool", "")
                level_str = rule.get("level", "allow").upper()
                overrides[tool_name] = getattr(PermissionLevel, level_str, PermissionLevel.ALLOW)

        section = PermissionsSection(
            default_level=default,
            tool_overrides=overrides,
        )
        return PermissionEngine(config=section)
    except ImportError:
        return _FallbackPermissionEngine(rules=rules)


def check_permission(engine: Any, agent_id: str, tool_name: str) -> bool:
    """Check whether *agent_id* is permitted to use *tool_name* (patchable)."""
    if isinstance(engine, _FallbackPermissionEngine):
        return engine.check(agent_id, tool_name)
    try:
        return engine.check(agent_id=agent_id, tool_name=tool_name)
    except Exception:  # noqa: BLE001
        return True


# ---------------------------------------------------------------------------
# Fallback implementation
# ---------------------------------------------------------------------------


class _FallbackPermissionEngine:
    """Simple rule-based permission engine used when runtime is unavailable."""

    def __init__(self, rules: list[dict[str, Any]]) -> None:
        self._rules: list[dict[str, Any]] = rules
        self._default = "allow"
        for rule in rules:
            if rule.get("scope") == "default":
                self._default = rule.get("level", "allow").lower()

    def check(self, agent_id: str, tool_name: str) -> bool:
        for rule in self._rules:
            if rule.get("scope") == "default":
                continue
            if self._matches(rule, agent_id, tool_name):
                return rule.get("level", "allow").lower() == "allow"
        return self._default == "allow"

    def _matches(self, rule: dict[str, Any], agent_id: str, tool_name: str) -> bool:
        tool_pat = rule.get("tool", "*")
        agent_pat = rule.get("agent", "*")
        tool_ok = tool_pat == "*" or tool_pat == tool_name
        agent_ok = agent_pat == "*" or agent_pat == agent_id
        return tool_ok and agent_ok

    @property
    def config(self) -> Any:
        return None

    @property
    def _host(self) -> Any:
        return None
