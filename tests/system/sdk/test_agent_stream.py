"""System tests for Agent.stream() — requires a running JiuwenSwarm server.

These tests are skipped automatically when the runtime is not available.
Run with::

    pytest -m system tests/system/sdk/test_agent_stream.py
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.system


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _runtime_available() -> bool:
    try:
        import openjiuwen.core  # noqa: F401

        return True
    except ImportError:
        return False


skip_no_runtime = pytest.mark.skipif(
    not _runtime_available(),
    reason="JiuwenSwarm runtime not installed",
)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@skip_no_runtime
async def test_agent_stream_yields_chunks():
    """Agent.stream() should yield at least one chunk dict."""
    from openjiuwen.sdk import Agent, ModelConfig

    model = ModelConfig.from_env()
    agent = await Agent.create("stream-test", model=model)

    chunks = []
    async for chunk in agent.stream("Say hello in one word."):
        chunks.append(chunk)
        if len(chunks) >= 5:  # don't run to completion in system test
            break

    assert len(chunks) > 0, "Expected at least one streamed chunk"
    assert isinstance(chunks[0], dict), "Chunks should be dicts"


@pytest.mark.asyncio
@skip_no_runtime
async def test_agent_stream_chunk_has_text_or_chunk_key():
    from openjiuwen.sdk import Agent, ModelConfig

    model = ModelConfig.from_env()
    agent = await Agent.create("stream-chunk-test", model=model)

    async for chunk in agent.stream("Say hi."):
        assert any(key in chunk for key in ("text", "chunk", "data")), (
            f"Unexpected chunk format: {chunk}"
        )
        break


@pytest.mark.asyncio
@skip_no_runtime
async def test_agent_stream_session_continuity():
    """Streaming with a fixed session_id should continue the same session."""
    import uuid
    from openjiuwen.sdk import Agent, ModelConfig

    model = ModelConfig.from_env()
    agent = await Agent.create("stream-session", model=model)
    session_id = f"sys-test-{uuid.uuid4().hex[:8]}"

    chunks_run1 = []
    async for chunk in agent.stream("My name is Alice.", session_id=session_id):
        chunks_run1.append(chunk)
        if len(chunks_run1) >= 3:
            break

    # Second stream continues same session
    chunks_run2 = []
    async for chunk in agent.stream("What is my name?", session_id=session_id):
        chunks_run2.append(chunk)
        if len(chunks_run2) >= 3:
            break

    assert len(chunks_run2) > 0
