"""Shared fixtures for gateway unit tests."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from openjiuwen.gateway.app import build_gateway_app
from openjiuwen.gateway.config import AgentSpec, GatewayConfig
from openjiuwen.sdk.core.agent import AgentResult
from openjiuwen.sdk.core.config import ModelConfig


# ---------------------------------------------------------------------------
# Mock agent
# ---------------------------------------------------------------------------


class MockAgent:
    """Minimal Agent substitute for gateway tests."""

    async def run(self, prompt: str, *, session_id: str | None = None) -> AgentResult:
        return AgentResult(
            text=f"echo: {prompt}",
            session_id=session_id or "sess_mock",
            metadata={"mock": True},
        )

    async def stream(self, prompt: str, *, session_id: str | None = None):
        for word in ("echo", ": ", prompt):
            yield word

    async def checkpoint(self) -> str:
        import uuid
        return f"ckpt_mock_{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Factory patch
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=False)
def patch_agent_factory(monkeypatch):
    """Replace _agent_factory with one that returns MockAgent without a runtime."""
    import openjiuwen.gateway._registry as _reg

    async def _fake_factory(name, *, model, tools, system_prompt, **_):
        return MockAgent()

    monkeypatch.setattr(_reg, "_agent_factory", _fake_factory)


# ---------------------------------------------------------------------------
# Model config stub
# ---------------------------------------------------------------------------

_STUB_MODEL = ModelConfig(provider="openai", model="gpt-4o")

# ---------------------------------------------------------------------------
# App fixtures (no auth / with auth)
# ---------------------------------------------------------------------------


@pytest.fixture()
def agent_spec() -> AgentSpec:
    return AgentSpec(id="echo", name="EchoAgent", model=_STUB_MODEL)


@pytest.fixture()
def app_no_auth(agent_spec, patch_agent_factory):
    config = GatewayConfig(auth_token=None, agents=[agent_spec])
    return build_gateway_app(config)


@pytest.fixture()
def app_with_auth(agent_spec, patch_agent_factory):
    config = GatewayConfig(auth_token="test-token", agents=[agent_spec])
    return build_gateway_app(config)


@pytest.fixture()
def client(app_no_auth) -> TestClient:
    return TestClient(app_no_auth, raise_server_exceptions=True)


@pytest.fixture()
def auth_client(app_with_auth) -> TestClient:
    return TestClient(app_with_auth, raise_server_exceptions=True)
