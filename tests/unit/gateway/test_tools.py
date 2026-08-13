"""Tests for GET /v1/tools."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from openjiuwen.gateway.app import build_gateway_app
from openjiuwen.gateway.config import AgentSpec, GatewayConfig
from openjiuwen.sdk.core.config import ModelConfig
from openjiuwen.sdk.core.tools import SdkTool, tool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@tool
def add(x: int, y: int) -> int:
    """Add two numbers."""
    return x + y


@tool
def greet(name: str) -> str:
    """Say hello."""
    return f"Hello, {name}"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_list_tools_empty_when_no_tools(client):
    resp = client.get("/v1/tools")
    assert resp.status_code == 200
    assert resp.json()["tools"] == []


def test_list_tools_returns_registered_tools(patch_agent_factory):
    model = ModelConfig(provider="openai", model="gpt-4o")
    spec = AgentSpec(id="a", name="Agent", model=model, tools=[add, greet])
    app = build_gateway_app(GatewayConfig(auth_token=None, agents=[spec]))
    c = TestClient(app, raise_server_exceptions=True)

    resp = c.get("/v1/tools")
    assert resp.status_code == 200
    names = {t["name"] for t in resp.json()["tools"]}
    assert "add" in names
    assert "greet" in names


def test_list_tools_deduplicates_across_agents(patch_agent_factory):
    """Same tool on two agents appears only once."""
    model = ModelConfig(provider="openai", model="gpt-4o")
    spec_a = AgentSpec(id="a", name="A", model=model, tools=[add])
    spec_b = AgentSpec(id="b", name="B", model=model, tools=[add])
    app = build_gateway_app(GatewayConfig(auth_token=None, agents=[spec_a, spec_b]))
    c = TestClient(app, raise_server_exceptions=True)

    tools = c.get("/v1/tools").json()["tools"]
    assert sum(1 for t in tools if t["name"] == "add") == 1
