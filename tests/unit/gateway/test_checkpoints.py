"""Tests for checkpoint REST routes."""

from __future__ import annotations


def test_list_checkpoints_initially_empty(client):
    resp = client.get("/v1/checkpoints")
    assert resp.status_code == 200
    assert resp.json()["checkpoints"] == []


def test_save_checkpoint(client):
    resp = client.post("/v1/agents/echo/checkpoint")
    assert resp.status_code == 201
    ckpt = resp.json()["checkpoint"]
    assert "id" in ckpt
    assert ckpt["agent_id"] == "echo"
    assert "created_at" in ckpt


def test_save_checkpoint_unknown_agent_404(client):
    resp = client.post("/v1/agents/ghost/checkpoint")
    assert resp.status_code == 404


def test_list_checkpoints_after_save(client):
    client.post("/v1/agents/echo/checkpoint")
    client.post("/v1/agents/echo/checkpoint")
    resp = client.get("/v1/checkpoints")
    assert len(resp.json()["checkpoints"]) == 2


def test_restore_checkpoint(client, monkeypatch):
    # Save first
    ckpt_id = client.post("/v1/agents/echo/checkpoint").json()["checkpoint"]["id"]

    # Patch Agent.restore to return the mock agent
    from tests.unit.gateway.conftest import MockAgent

    async def _fake_restore(checkpoint_id, *, model=None):
        return MockAgent()

    monkeypatch.setattr(
        "openjiuwen.sdk.core.agent.Agent.restore",
        _fake_restore,
        raising=True,
    )

    resp = client.post(f"/v1/checkpoints/{ckpt_id}/restore")
    assert resp.status_code == 201
    data = resp.json()
    assert data["restored"] is True
    assert data["checkpoint_id"] == ckpt_id


def test_restore_unknown_checkpoint_404(client):
    resp = client.post("/v1/checkpoints/ckpt_ghost/restore")
    assert resp.status_code == 404
