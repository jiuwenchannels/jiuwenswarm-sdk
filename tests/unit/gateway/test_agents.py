"""Tests for agent management and run/stream endpoints."""

from __future__ import annotations

import json


def test_list_agents_returns_registered(client):
    resp = client.get("/v1/agents")
    assert resp.status_code == 200
    agents = resp.json()["agents"]
    assert len(agents) == 1
    assert agents[0]["id"] == "echo"


def test_get_agent_by_id(client):
    resp = client.get("/v1/agents/echo")
    assert resp.status_code == 200
    agent = resp.json()["agent"]
    assert agent["id"] == "echo"
    assert agent["name"] == "EchoAgent"


def test_get_agent_not_found_404(client):
    resp = client.get("/v1/agents/ghost")
    assert resp.status_code == 404


def test_run_agent_returns_text(client):
    resp = client.post("/v1/agents/echo/run", json={"prompt": "hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert "hello" in data["text"]
    assert "session_id" in data


def test_run_agent_not_found_404(client):
    resp = client.post("/v1/agents/ghost/run", json={"prompt": "x"})
    assert resp.status_code == 404


def test_run_agent_with_session_id(client):
    resp = client.post(
        "/v1/agents/echo/run",
        json={"prompt": "ctx", "session_id": "sess_explicit"},
    )
    assert resp.status_code == 200
    assert resp.json()["session_id"] == "sess_explicit"


def test_stream_agent_returns_sse(client):
    resp = client.post("/v1/agents/echo/stream", json={"prompt": "stream me"})
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]


def test_stream_agent_contains_tokens(client):
    raw = client.post("/v1/agents/echo/stream", json={"prompt": "x"}).text
    events = [line for line in raw.splitlines() if line.startswith("event:")]
    assert any(e == "event: token" for e in events)
    assert any(e == "event: done" for e in events)


def test_stream_agent_not_found_404(client):
    resp = client.post("/v1/agents/ghost/stream", json={"prompt": "x"})
    assert resp.status_code == 404
