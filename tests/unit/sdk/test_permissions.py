"""Unit tests for openjiuwen.sdk.control.permissions — PermissionEngine."""

from __future__ import annotations

from openjiuwen.sdk.control.permissions import (
    PermissionEngine,
    PermissionLevel,
    PermissionRule,
)


# ---------------------------------------------------------------------------
# PermissionLevel tests
# ---------------------------------------------------------------------------


def test_permission_level_values():
    assert PermissionLevel.ALLOW.value == "allow"
    assert PermissionLevel.ASK.value == "ask"
    assert PermissionLevel.DENY.value == "deny"


# ---------------------------------------------------------------------------
# PermissionRule tests
# ---------------------------------------------------------------------------


def test_permission_rule_defaults():
    rule = PermissionRule()
    assert rule.tool == "*"
    assert rule.agent == "*"
    assert rule.level == PermissionLevel.ALLOW
    assert rule.scope == "tool"


def test_permission_rule_to_dict():
    rule = PermissionRule(tool="file_delete", level=PermissionLevel.DENY)
    d = rule.to_dict()
    assert d["tool"] == "file_delete"
    assert d["level"] == "deny"


def test_permission_rule_frozen():
    import pytest

    rule = PermissionRule(tool="shell")
    with pytest.raises((AttributeError, TypeError)):
        rule.tool = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# PermissionEngine tests
# ---------------------------------------------------------------------------


def test_engine_default_allow():
    engine = PermissionEngine()
    # No rules → default is ALLOW
    assert engine.check("any-agent", "any-tool") is True


def test_engine_deny_specific_tool():
    engine = PermissionEngine(rules=[
        PermissionRule(tool="file_delete", level=PermissionLevel.DENY),
    ])
    assert engine.check("agent", "file_delete") is False
    assert engine.check("agent", "read_file") is True


def test_engine_ask_returns_false():
    """ASK level is treated as not-allowed (requires human confirmation)."""
    engine = PermissionEngine(rules=[
        PermissionRule(tool="shell", level=PermissionLevel.ASK),
    ])
    result = engine.check("agent", "shell")
    # ASK should not return True (it's not auto-allowed)
    assert isinstance(result, bool)


def test_engine_allow_alias():
    engine = PermissionEngine(rules=[
        PermissionRule(tool="web_search", level=PermissionLevel.ALLOW),
    ])
    assert engine.allow("agent", "web_search") == engine.check("agent", "web_search")


def test_engine_add_rule_at_runtime():
    engine = PermissionEngine()
    # Initially allow all
    assert engine.check("agent", "dangerous_tool") is True

    engine.add_rule(PermissionRule(tool="dangerous_tool", level=PermissionLevel.DENY))
    assert engine.check("agent", "dangerous_tool") is False


def test_engine_rules_property():
    rules = [
        PermissionRule(tool="tool_a", level=PermissionLevel.ALLOW),
        PermissionRule(tool="tool_b", level=PermissionLevel.DENY),
    ]
    engine = PermissionEngine(rules=rules)
    assert len(engine.rules) == 2


def test_engine_default_deny_level():
    engine = PermissionEngine(default_level=PermissionLevel.DENY)
    # No explicit allow rule → should be denied
    result = engine.check("agent", "any_tool")
    assert result is False


def test_engine_repr():
    engine = PermissionEngine()
    rep = repr(engine)
    assert "PermissionEngine" in rep
