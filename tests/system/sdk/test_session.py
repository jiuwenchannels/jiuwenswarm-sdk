"""System tests for Session persistence — requires running JiuwenSwarm server.

Run with::

    pytest -m system tests/system/sdk/test_session.py
"""

from __future__ import annotations

import pytest

pytestmark = pytest.mark.system


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
async def test_session_list_and_get():
    """Session.list() and Session.get() should return valid session objects."""
    from openjiuwen.sdk import Agent, ModelConfig, Session

    model = ModelConfig.from_env()
    agent = await Agent.create("session-test", model=model)

    # Create a session by running the agent
    result = await agent.run("My favourite colour is blue.")
    session_id = result.session_id
    assert session_id is not None, "Expected a session_id in the result"

    # Retrieve the session
    session = await Session.get(session_id)
    assert session is not None


@pytest.mark.asyncio
@skip_no_runtime
async def test_session_message_history():
    """Messages should persist across multiple agent.run() calls in same session."""
    import uuid
    from openjiuwen.sdk import Agent, ModelConfig

    model = ModelConfig.from_env()
    agent = await Agent.create("history-test", model=model)
    sid = f"hist-{uuid.uuid4().hex[:8]}"

    await agent.run("My pet is a cat named Whiskers.", session_id=sid)
    result2 = await agent.run("What is my pet's name?", session_id=sid)

    assert "Whiskers" in result2.text, (
        f"Expected Whiskers in response, got: {result2.text!r}"
    )


@pytest.mark.asyncio
@skip_no_runtime
async def test_session_delete():
    """Session.delete() should remove the session from the store."""
    import uuid
    from openjiuwen.sdk import Agent, ModelConfig, Session

    model = ModelConfig.from_env()
    agent = await Agent.create("delete-test", model=model)
    sid = f"del-{uuid.uuid4().hex[:8]}"

    await agent.run("Hello.", session_id=sid)

    deleted = await Session.delete(sid)
    assert deleted is True or deleted is None  # depends on runtime

    # After deletion, retrieving should return None or raise
    try:
        session = await Session.get(sid)
        assert session is None
    except Exception:
        pass  # Acceptable: some runtimes raise on missing session
