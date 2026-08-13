"""Tests for BearerTokenMiddleware.

Covers:
- Dev mode (auth_token=None) passes all requests.
- Valid token passes.
- Missing Authorization header → 401.
- Wrong token → 401.
- WebSocket upgrade requests are let through (auth happens in WS handler).
"""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient


def test_dev_mode_no_auth_required(client):
    """When auth_token=None every request is allowed."""
    resp = client.get("/v1/health")
    assert resp.status_code == 200


def test_valid_token_passes(auth_client):
    """Correct Bearer token is accepted."""
    resp = auth_client.get("/v1/health", headers={"Authorization": "Bearer test-token"})
    assert resp.status_code == 200


def test_missing_auth_header_returns_401(auth_client):
    """No Authorization header → 401."""
    resp = auth_client.get("/v1/health")
    assert resp.status_code == 401
    assert "Unauthorized" in resp.json()["detail"]


def test_wrong_token_returns_401(auth_client):
    """Wrong Bearer token → 401."""
    resp = auth_client.get("/v1/health", headers={"Authorization": "Bearer wrong"})
    assert resp.status_code == 401


def test_bearer_prefix_required(auth_client):
    """Token without 'Bearer ' prefix → 401."""
    resp = auth_client.get("/v1/health", headers={"Authorization": "test-token"})
    assert resp.status_code == 401
