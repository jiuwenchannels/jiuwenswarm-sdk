"""Unit tests for openjiuwen.sdk.lsp — LSPIntegration façade."""

from __future__ import annotations

import pytest

from openjiuwen.sdk.lsp import (
    LSPCompletionItem,
    LSPDiagnostic,
    LSPIntegration,
    LSPPosition,
    LSPRange,
    _FallbackLSPBridge,
    _call_lsp_complete,
    _call_lsp_diagnose,
)


# ---------------------------------------------------------------------------
# Data type tests
# ---------------------------------------------------------------------------


def test_lsp_position():
    pos = LSPPosition(line=10, character=4)
    assert pos.line == 10
    assert pos.character == 4


def test_lsp_range():
    start = LSPPosition(0, 0)
    end = LSPPosition(0, 10)
    rng = LSPRange(start=start, end=end)
    assert rng.start == start
    assert rng.end == end


def test_lsp_diagnostic_defaults():
    diag = LSPDiagnostic(message="undefined variable 'x'")
    assert diag.severity == "error"
    assert diag.source == ""
    assert diag.code is None


def test_lsp_completion_item_defaults():
    item = LSPCompletionItem(label="print")
    assert item.kind == "text"
    assert item.detail == ""
    assert item.documentation == ""


# ---------------------------------------------------------------------------
# Fallback bridge tests
# ---------------------------------------------------------------------------


def test_fallback_bridge_complete_returns_empty():
    bridge = _FallbackLSPBridge(["pyright-langserver", "--stdio"])
    result = bridge.complete(uri="src/main.py", line=0, character=0)
    assert result == []


def test_fallback_bridge_diagnose_returns_empty():
    bridge = _FallbackLSPBridge(["pyright-langserver", "--stdio"])
    result = bridge.diagnose(uri="src/main.py")
    assert result == []


def test_fallback_bridge_shutdown_noop():
    bridge = _FallbackLSPBridge([])
    bridge.shutdown()  # should not raise


# ---------------------------------------------------------------------------
# _call_lsp_complete / _call_lsp_diagnose patchable function tests
# ---------------------------------------------------------------------------


def test_call_lsp_complete_no_method():
    """Bridge without complete() returns empty list."""
    result = _call_lsp_complete(object(), "file.py", LSPPosition(0, 0))
    assert result == []


def test_call_lsp_complete_with_bridge():
    class MockBridge:
        def complete(self, uri, line, character):
            return ["print", "pass"]

    pos = LSPPosition(0, 0)
    items = _call_lsp_complete(MockBridge(), "file.py", pos)
    assert len(items) == 2
    assert items[0].label == "print"


def test_call_lsp_diagnose_dict_format():
    class MockBridge:
        def diagnose(self, uri):
            return [{"message": "error here", "severity": "error", "source": "pyright"}]

    diags = _call_lsp_diagnose(MockBridge(), "file.py")
    assert len(diags) == 1
    assert diags[0].message == "error here"
    assert diags[0].source == "pyright"


def test_call_lsp_diagnose_lsp_diagnostic_passthrough():
    diag = LSPDiagnostic(message="type error", severity="warning")

    class MockBridge:
        def diagnose(self, uri):
            return [diag]

    result = _call_lsp_diagnose(MockBridge(), "file.py")
    assert result[0] is diag


def test_call_lsp_diagnose_exception_swallowed():
    class BadBridge:
        def diagnose(self, uri):
            raise RuntimeError("server crashed")

    result = _call_lsp_diagnose(BadBridge(), "file.py")
    assert result == []


# ---------------------------------------------------------------------------
# LSPIntegration.attach tests
# ---------------------------------------------------------------------------


def test_lsp_attach_returns_integration():
    agent = object()
    lsp = LSPIntegration.attach(agent, server_cmd=["echo"])
    assert isinstance(lsp, LSPIntegration)


def test_lsp_attach_string_cmd():
    lsp = LSPIntegration.attach(object(), server_cmd="pyright-langserver")
    assert isinstance(lsp, LSPIntegration)


def test_lsp_repr():
    lsp = LSPIntegration.attach(object(), server_cmd=["pyright"])
    rep = repr(lsp)
    assert "LSPIntegration" in rep
    assert "pyright" in rep


# ---------------------------------------------------------------------------
# LSPIntegration async API
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lsp_complete_returns_list():
    agent = object()
    lsp = LSPIntegration.attach(agent, server_cmd=["echo"])
    result = await lsp.complete("src/main.py", line=0, character=0)
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_lsp_diagnose_returns_list():
    agent = object()
    lsp = LSPIntegration.attach(agent, server_cmd=["echo"])
    result = await lsp.diagnose("src/main.py")
    assert isinstance(result, list)


@pytest.mark.asyncio
async def test_lsp_shutdown():
    lsp = LSPIntegration.attach(object(), server_cmd=["echo"])
    await lsp.shutdown()  # should not raise
