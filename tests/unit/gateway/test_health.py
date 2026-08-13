"""Tests for GET /v1/health."""

from __future__ import annotations


def test_health_returns_ok(client):
    resp = client.get("/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


def test_health_includes_version(client):
    data = client.get("/v1/health").json()
    assert "version" in data
    assert isinstance(data["version"], str)


def test_health_includes_protocol_version(client):
    data = client.get("/v1/health").json()
    assert data["protocol_version"] == "1"
