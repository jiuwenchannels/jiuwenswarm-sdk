"""Remote (WebSocket/REST) bridge.

Implements the JiuwenSwarm WebSocket envelope protocol so that
:meth:`Agent.connect` can drive a remote server with the same API as the
in-process :meth:`Agent.create`.

Envelope protocol (JSON, newline-delimited over WebSocket)
----------------------------------------------------------
Client → Server::

    {"type": "chat", "session_id": "sess_...", "message": "...", "mode": "default"}

Server → Client (stream of envelopes)::

    {"type": "ack",   "session_id": "sess_..."}
    {"type": "token", "text": "..."}
    ...
    {"type": "done",  "session_id": "sess_..."}
    {"type": "error", "message": "..."}

Session management messages::

    Client: {"type": "sessions"}
    Server: {"type": "sessions", "sessions": [...]}

    Client: {"type": "create_session", "title": "...", "mode": "default"}
    Server: {"type": "session_created", "session": {...}}
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, AsyncIterator

if TYPE_CHECKING:
    from openjiuwen.sdk.core.config import RemoteConfig

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# WebSocket connection wrapper
# ---------------------------------------------------------------------------


@dataclass
class RemoteHandle:
    """Internal state for one remote :class:`~openjiuwen.sdk.core.agent.Agent`."""

    server_url: str
    auth_token: str | None
    timeout: float
    max_retries: int

    _ws: Any = field(default=None, init=False, repr=False)
    _active_session_id: str | None = field(default=None, init=False)
    _lock: asyncio.Lock = field(default_factory=asyncio.Lock, init=False, repr=False)

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self) -> None:
        """Open the WebSocket connection."""
        ws_url = self._ws_url()
        try:
            import websockets  # type: ignore[import-untyped]
        except ImportError as exc:
            from openjiuwen.sdk.core.errors import ConnectionError

            raise ConnectionError(
                "websockets package is required for remote mode.  "
                "Install it with: pip install websockets"
            ) from exc

        headers: dict[str, str] = {}
        if self.auth_token:
            headers["Authorization"] = f"Bearer {self.auth_token}"

        try:
            self._ws = await websockets.connect(
                ws_url,
                additional_headers=headers,
                open_timeout=self.timeout,
                close_timeout=10.0,
            )
            log.debug("[sdk/remote] connected to %s", ws_url)
        except Exception as exc:
            from openjiuwen.sdk.core.errors import ConnectionError

            raise ConnectionError(f"Cannot connect to {ws_url}: {exc}") from exc

    async def disconnect(self) -> None:
        """Close the WebSocket connection gracefully."""
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:  # noqa: BLE001
                pass
            self._ws = None

    def _ws_url(self) -> str:
        """Return the WS URL, upgrading http(s) to ws(s) if needed."""
        url = self.server_url
        if url.startswith("http://"):
            url = "ws://" + url[7:]
        elif url.startswith("https://"):
            url = "wss://" + url[8:]
        # Ensure path ends with /v1/ws
        if not url.endswith("/v1/ws"):
            url = url.rstrip("/") + "/v1/ws"
        return url

    async def _ensure_connected(self) -> None:
        if self._ws is None or not self._ws.open:
            await self.connect()

    # ------------------------------------------------------------------
    # Send / receive helpers
    # ------------------------------------------------------------------

    async def _send(self, payload: dict[str, Any]) -> None:
        await self._ensure_connected()
        await self._ws.send(json.dumps(payload))

    async def _recv(self) -> dict[str, Any]:
        raw = await asyncio.wait_for(self._ws.recv(), timeout=self.timeout)
        return json.loads(raw)

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    async def list_sessions(self) -> list[dict[str, Any]]:
        await self._send({"type": "sessions"})
        while True:
            env = await self._recv()
            if env.get("type") == "sessions":
                return env.get("sessions", [])
            if env.get("type") == "error":
                _raise_server_error(env)

    async def create_session(self, title: str, mode: str = "default") -> dict[str, Any]:
        await self._send({"type": "create_session", "title": title, "mode": mode})
        while True:
            env = await self._recv()
            if env.get("type") in ("session_created", "ack"):
                sess = env.get("session", env)
                self._active_session_id = sess.get("session_id") or sess.get("id")
                return sess
            if env.get("type") == "error":
                _raise_server_error(env)

    async def set_active_session(self, session_id: str) -> None:
        self._active_session_id = session_id

    # ------------------------------------------------------------------
    # Run (non-streaming)
    # ------------------------------------------------------------------

    async def run(self, prompt: str, session_id: str | None = None) -> "RemoteRunResult":
        sid = session_id or self._active_session_id
        if sid is None:
            # Auto-create a session
            sess = await self.create_session(title="SDK session")
            sid = sess.get("session_id") or sess.get("id") or f"sess_{uuid.uuid4().hex[:12]}"
            self._active_session_id = sid

        await self._send({"type": "chat", "session_id": sid, "message": prompt, "mode": "default"})

        tokens: list[str] = []
        async with self._lock:
            while True:
                env = await self._recv()
                t = env.get("type")
                if t == "token":
                    tokens.append(env.get("text", ""))
                elif t in ("done", "ack") and "session_id" in env:
                    break
                elif t == "done":
                    break
                elif t == "error":
                    _raise_server_error(env)

        return RemoteRunResult(text="".join(tokens), session_id=sid)

    # ------------------------------------------------------------------
    # Stream
    # ------------------------------------------------------------------

    async def stream(self, prompt: str, session_id: str | None = None) -> AsyncIterator[str]:
        sid = session_id or self._active_session_id
        if sid is None:
            sess = await self.create_session(title="SDK session")
            sid = sess.get("session_id") or sess.get("id") or f"sess_{uuid.uuid4().hex[:12]}"
            self._active_session_id = sid

        await self._send({"type": "chat", "session_id": sid, "message": prompt, "mode": "default"})

        while True:
            env = await self._recv()
            t = env.get("type")
            if t == "token":
                text = env.get("text", "")
                if text:
                    yield text
            elif t in ("done",):
                break
            elif t == "error":
                _raise_server_error(env)
            elif t == "ack":
                # ack just confirms the message was received; keep reading
                pass


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _raise_server_error(env: dict[str, Any]) -> None:
    from openjiuwen.sdk.core.errors import ServerError

    msg = env.get("message", env.get("error", "Unknown server error"))
    raise ServerError(msg)


@dataclass
class RemoteRunResult:
    """Result of a non-streaming remote run."""

    text: str
    session_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# REST helpers (used by Session.list / .get / .delete over HTTP)
# ---------------------------------------------------------------------------


async def _rest_request(
    method: str,
    url: str,
    auth_token: str | None = None,
    json_body: dict[str, Any] | None = None,
    timeout: float = 30.0,
) -> dict[str, Any]:
    """Make a single REST API call to the JiuwenSwarm gateway."""
    try:
        import httpx
    except ImportError as exc:
        from openjiuwen.sdk.core.errors import ConnectionError

        raise ConnectionError(
            "httpx package is required for REST calls.  Install: pip install httpx"
        ) from exc

    headers: dict[str, str] = {"Content-Type": "application/json"}
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"

    async with httpx.AsyncClient(timeout=timeout) as client:
        fn = getattr(client, method.lower())
        kwargs: dict[str, Any] = {"headers": headers}
        if json_body is not None:
            kwargs["json"] = json_body
        response: httpx.Response = await fn(url, **kwargs)

        if response.status_code >= 400:
            from openjiuwen.sdk.core.errors import ServerError

            raise ServerError(response.text, status_code=response.status_code)
        try:
            return response.json()
        except Exception:
            return {"text": response.text}
