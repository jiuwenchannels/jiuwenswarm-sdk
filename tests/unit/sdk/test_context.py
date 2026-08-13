"""Unit tests for openjiuwen.sdk.control.context — ContextEngine."""

from __future__ import annotations

import pytest

from openjiuwen.sdk.control.context import (
    ContextEngine,
    ContextEngineConfig,
    ContextStats,
)


# ---------------------------------------------------------------------------
# ContextEngineConfig
# ---------------------------------------------------------------------------


def test_context_engine_config_defaults():
    cfg = ContextEngineConfig()
    assert cfg.max_messages == 200
    assert cfg.token_limit == 32_000
    assert cfg.compression_ratio == 0.5


def test_context_engine_config_frozen():
    cfg = ContextEngineConfig()
    with pytest.raises((AttributeError, TypeError)):
        cfg.max_messages = 10  # type: ignore[misc]


# ---------------------------------------------------------------------------
# ContextStats
# ---------------------------------------------------------------------------


def test_context_stats_fields():
    stats = ContextStats(input_tokens=1000, output_tokens=500, compressions_applied=1)
    assert stats.input_tokens == 1000
    assert stats.output_tokens == 500
    assert stats.compressions_applied == 1


# ---------------------------------------------------------------------------
# ContextEngine — compress
# ---------------------------------------------------------------------------


def test_compress_within_limit():
    engine = ContextEngine(ContextEngineConfig(max_messages=100))
    messages = [{"role": "user", "content": f"msg {i}"} for i in range(5)]
    result = engine.compress(messages)
    assert len(result) == 5  # no truncation needed


def test_compress_trims_to_max_messages():
    engine = ContextEngine(ContextEngineConfig(max_messages=3))
    messages = [{"role": "user", "content": f"msg {i}"} for i in range(10)]
    result = engine.compress(messages)
    assert len(result) == 3
    # Should keep the most recent messages
    assert result[-1]["content"] == "msg 9"


def test_compress_updates_last_stats():
    engine = ContextEngine(ContextEngineConfig(max_messages=3))
    messages = [{"role": "user", "content": f"m{i}"} for i in range(6)]
    engine.compress(messages)
    assert engine.last_stats is not None
    assert engine.last_stats.compressions_applied >= 1


def test_compress_empty_messages():
    engine = ContextEngine()
    result = engine.compress([])
    assert result == []


# ---------------------------------------------------------------------------
# ContextEngine — inject
# ---------------------------------------------------------------------------


def test_inject_prepends_system_message():
    engine = ContextEngine()
    messages = [{"role": "user", "content": "Hello"}]
    result = engine.inject(messages, "You are a helpful assistant.")
    assert result[0]["role"] == "system"
    assert result[0]["content"] == "You are a helpful assistant."
    assert len(result) == 2


def test_inject_preserves_existing_messages():
    engine = ContextEngine()
    messages = [
        {"role": "user", "content": "Q1"},
        {"role": "assistant", "content": "A1"},
    ]
    result = engine.inject(messages, "system context")
    assert len(result) == 3
    assert result[1]["content"] == "Q1"


# ---------------------------------------------------------------------------
# ContextEngine — token_count
# ---------------------------------------------------------------------------


def test_token_count_heuristic():
    engine = ContextEngine()
    # "hello" = 5 chars → ~1 token; 4 chars/token heuristic
    messages = [{"role": "user", "content": "1234"}]
    count = engine.token_count(messages)
    assert count == 1  # 4 chars // 4


def test_token_count_empty():
    engine = ContextEngine()
    count = engine.token_count([])
    assert count == 0


# ---------------------------------------------------------------------------
# ContextEngine — repr
# ---------------------------------------------------------------------------


def test_context_engine_repr():
    engine = ContextEngine(ContextEngineConfig(token_limit=8000, max_messages=50))
    rep = repr(engine)
    assert "8000" in rep
    assert "50" in rep
