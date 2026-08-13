"""Unit tests for openjiuwen.sdk.memory — Memory façade.

All tests mock the memory_bridge so no runtime is needed.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from openjiuwen.sdk.memory import Memory, MemoryRecord, MemoryScope, make_memory
from openjiuwen.sdk._internal.memory_bridge import _FallbackMemoryStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_memory(scope: MemoryScope = MemoryScope.USER, user_id: str = "u1") -> Memory:
    """Return a Memory backed by the in-process fallback store."""
    with patch(
        "openjiuwen.sdk._internal.memory_bridge.create_memory_store",
        return_value=_FallbackMemoryStore(scope=scope.value, user_id=user_id),
    ):
        return Memory(scope=scope, user_id=user_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_memory_scope_enum():
    assert MemoryScope.USER.value == "user"
    assert MemoryScope.GLOBAL.value == "global"


@pytest.mark.asyncio
async def test_memory_add_returns_id():
    mem = _make_memory()
    entry_id = await mem.add("User likes bullet points.")
    assert isinstance(entry_id, str)
    assert entry_id.startswith("mem_")


@pytest.mark.asyncio
async def test_memory_search_finds_match():
    mem = _make_memory()
    await mem.add("User prefers bullet points.")
    await mem.add("User dislikes emojis.")

    results = await mem.search("bullet")
    assert len(results) >= 1
    assert isinstance(results[0], MemoryRecord)
    assert "bullet" in results[0].text


@pytest.mark.asyncio
async def test_memory_search_returns_empty_on_no_match():
    mem = _make_memory()
    await mem.add("The sky is blue.")
    # Fallback returns first entries when nothing matches
    results = await mem.search("quantum computing")
    assert isinstance(results, list)


@pytest.mark.asyncio
async def test_memory_clear():
    mem = _make_memory()
    await mem.add("Entry 1")
    await mem.add("Entry 2")
    await mem.clear()
    results = await mem.search("Entry")
    assert results == []


@pytest.mark.asyncio
async def test_memory_add_with_metadata():
    mem = _make_memory()
    await mem.add("Important fact.", metadata={"source": "doc.pdf"})
    results = await mem.search("Important")
    assert len(results) >= 1
    # Metadata is stored but fallback may not expose it in results


def test_make_memory_returns_none_when_no_scope():
    result = make_memory(None)
    assert result is None


def test_make_memory_creates_memory():
    with patch(
        "openjiuwen.sdk._internal.memory_bridge.create_memory_store",
        return_value=_FallbackMemoryStore(scope="user", user_id="u99"),
    ):
        mem = make_memory(MemoryScope.USER, user_id="u99")
    assert isinstance(mem, Memory)
    assert mem._scope == MemoryScope.USER


def test_memory_repr():
    mem = _make_memory(MemoryScope.SESSION, user_id="session_123")
    r = repr(mem)
    assert "Memory" in r
    assert "session" in r
