"""Tests for WebSocket gateway endpoint and envelope protocol."""

from __future__ import annotations

import json

import pytest

from openjiuwen.gateway.ws.envelope import (
    ProtocolError,
    make_ack,
    make_done,
    make_error,
    make_token,
    parse_envelope,
    serialise,
)


# ===========================================================================
# Envelope unit tests (no server needed)
# ===========================================================================


class TestParseEnvelope:
    def test_valid_envelope(self):
        env = parse_envelope('{"type": "chat", "message": "hi"}')
        assert env["type"] == "chat"
        assert env["message"] == "hi"

    def test_missing_type_raises(self):
        with pytest.raises(ProtocolError, match="missing"):
            parse_envelope('{"message": "hi"}')

    def test_malformed_json_raises(self):
        with pytest.raises(ProtocolError, match="Malformed"):
            parse_envelope("{not json}")

    def test_non_dict_raises(self):
        with pytest.raises(ProtocolError, match="JSON object"):
            parse_envelope("[1, 2, 3]")

    def test_empty_type_raises(self):
        with pytest.raises(ProtocolError, match="non-empty"):
            parse_envelope('{"type": ""}')


class TestMakeHelpers:
    def test_make_ack_has_protocol_version(self):
        env = make_ack()
        assert env["type"] == "ack"
        assert env["protocol_version"] == "1"

    def test_make_ack_with_client_type(self):
        env = make_ack(client_type="browser")
        assert env["client_type"] == "browser"

    def test_make_ack_with_session_id(self):
        env = make_ack(session_id="sess_abc")
        assert env["session_id"] == "sess_abc"

    def test_make_token(self):
        env = make_token("hello ")
        assert env == {"type": "token", "text": "hello "}

    def test_make_done(self):
        env = make_done("sess_123")
        assert env == {"type": "done", "session_id": "sess_123"}

    def test_make_error(self):
        env = make_error("oops")
        assert env == {"type": "error", "message": "oops"}

    def test_serialise(self):
        env = {"type": "ack"}
        assert json.loads(serialise(env)) == env


# ===========================================================================
# WebSocket integration tests (TestClient)
# ===========================================================================


def _send(ws, payload: dict) -> None:
    ws.send_text(json.dumps(payload))


def _recv(ws) -> dict:
    return json.loads(ws.receive_text())


class TestWsConnect:
    def test_connect_sends_ack(self, client):
        with client.websocket_connect("/v1/ws") as ws:
            _send(ws, {"type": "connect", "client_type": "test"})
            env = _recv(ws)
            assert env["type"] == "ack"
            assert env["protocol_version"] == "1"
            assert env["client_type"] == "test"

    def test_unknown_envelope_type_returns_error(self, client):
        with client.websocket_connect("/v1/ws") as ws:
            _send(ws, {"type": "unsupported_type"})
            env = _recv(ws)
            assert env["type"] == "error"

    def test_malformed_json_returns_error(self, client):
        with client.websocket_connect("/v1/ws") as ws:
            ws.send_text("{not json at all}")
            env = _recv(ws)
            assert env["type"] == "error"


class TestWsSessions:
    def test_sessions_list_returns_sessions_envelope(self, client):
        with client.websocket_connect("/v1/ws") as ws:
            _send(ws, {"type": "sessions"})
            env = _recv(ws)
            assert env["type"] == "sessions"
            assert isinstance(env["sessions"], list)

    def test_create_session_returns_session_created(self, client):
        with client.websocket_connect("/v1/ws") as ws:
            _send(ws, {
                "type": "create_session",
                "title": "WS test session",
                "agent_id": "echo",
                "mode": "default",
            })
            env = _recv(ws)
            assert env["type"] == "session_created"
            assert env["session"]["agent_id"] == "echo"

    def test_create_session_unknown_agent_returns_error(self, client):
        with client.websocket_connect("/v1/ws") as ws:
            _send(ws, {
                "type": "create_session",
                "agent_id": "ghost",
            })
            env = _recv(ws)
            assert env["type"] == "error"


class TestWsChat:
    def test_chat_streams_tokens_and_done(self, client):
        with client.websocket_connect("/v1/ws") as ws:
            # Create session first
            _send(ws, {
                "type": "create_session",
                "title": "chat",
                "agent_id": "echo",
            })
            session_env = _recv(ws)
            session_id = session_env["session"]["id"]

            # Send chat
            _send(ws, {
                "type": "chat",
                "session_id": session_id,
                "message": "Hello WS",
            })

            # Collect all envelopes until done
            envelopes = []
            env = _recv(ws)  # ack
            while True:
                envelopes.append(env)
                if env["type"] == "done":
                    break
                env = _recv(ws)

            types = [e["type"] for e in envelopes]
            assert "token" in types
            assert "done" in types

    def test_chat_without_session_returns_error(self, client):
        with client.websocket_connect("/v1/ws") as ws:
            _send(ws, {
                "type": "chat",
                "session_id": None,
                "message": "no session",
            })
            env = _recv(ws)
            assert env["type"] == "error"


class TestWsAuth:
    def test_connect_with_valid_token_accepted(self, auth_client):
        with auth_client.websocket_connect("/v1/ws") as ws:
            _send(ws, {
                "type": "connect",
                "client_type": "test",
                "token": "test-token",
            })
            env = _recv(ws)
            assert env["type"] == "ack"

    def test_connect_with_invalid_token_rejected(self, auth_client):
        with auth_client.websocket_connect("/v1/ws") as ws:
            _send(ws, {
                "type": "connect",
                "client_type": "test",
                "token": "wrong-token",
            })
            env = _recv(ws)
            assert env["type"] == "error"
