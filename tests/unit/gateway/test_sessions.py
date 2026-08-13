"""Tests for session CRUD and chat/stream endpoints."""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


def test_list_sessions_initially_empty(client):
    resp = client.get("/v1/sessions")
    assert resp.status_code == 200
    assert resp.json()["sessions"] == []


def test_create_session(client):
    resp = client.post(
        "/v1/sessions",
        json={"title": "Test session", "agent_id": "echo", "mode": "default"},
    )
    assert resp.status_code == 201
    session = resp.json()["session"]
    assert session["title"] == "Test session"
    assert session["agent_id"] == "echo"
    assert "id" in session
    assert session["id"].startswith("sess_")


def test_create_session_unknown_agent_404(client):
    resp = client.post(
        "/v1/sessions",
        json={"title": "x", "agent_id": "does-not-exist"},
    )
    assert resp.status_code == 404


def test_get_session(client):
    sid = client.post(
        "/v1/sessions",
        json={"title": "Retrieve me", "agent_id": "echo"},
    ).json()["session"]["id"]

    resp = client.get(f"/v1/sessions/{sid}")
    assert resp.status_code == 200
    assert resp.json()["session"]["id"] == sid


def test_get_session_not_found_404(client):
    resp = client.get("/v1/sessions/sess_doesnotexist")
    assert resp.status_code == 404


def test_list_sessions_after_create(client):
    client.post("/v1/sessions", json={"title": "A", "agent_id": "echo"})
    client.post("/v1/sessions", json={"title": "B", "agent_id": "echo"})
    resp = client.get("/v1/sessions")
    assert len(resp.json()["sessions"]) == 2


def test_delete_session(client):
    sid = client.post(
        "/v1/sessions", json={"title": "Delete me", "agent_id": "echo"}
    ).json()["session"]["id"]

    resp = client.delete(f"/v1/sessions/{sid}")
    assert resp.status_code == 200
    assert resp.json()["deleted"] is True

    # Should be gone now
    assert client.get(f"/v1/sessions/{sid}").status_code == 404


def test_delete_nonexistent_session_404(client):
    resp = client.delete("/v1/sessions/sess_ghost")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Chat (blocking)
# ---------------------------------------------------------------------------


def test_chat_returns_text(client):
    sid = client.post(
        "/v1/sessions", json={"title": "chat", "agent_id": "echo"}
    ).json()["session"]["id"]

    resp = client.post(f"/v1/sessions/{sid}/chat", json={"message": "hello"})
    assert resp.status_code == 200
    data = resp.json()
    assert "hello" in data["text"]
    assert data["session_id"] == sid


def test_chat_unknown_session_404(client):
    resp = client.post("/v1/sessions/sess_ghost/chat", json={"message": "x"})
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Stream (SSE)
# ---------------------------------------------------------------------------


def test_chat_stream_returns_sse(client):
    sid = client.post(
        "/v1/sessions", json={"title": "stream", "agent_id": "echo"}
    ).json()["session"]["id"]

    resp = client.post(
        f"/v1/sessions/{sid}/chat/stream",
        json={"message": "hi"},
    )
    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]


def test_chat_stream_contains_token_events(client):
    sid = client.post(
        "/v1/sessions", json={"title": "s", "agent_id": "echo"}
    ).json()["session"]["id"]

    raw = client.post(
        f"/v1/sessions/{sid}/chat/stream",
        json={"message": "ping"},
    ).text
    assert "event: token" in raw
    assert "event: done" in raw
