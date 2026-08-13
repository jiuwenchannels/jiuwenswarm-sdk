"""Bearer-token authentication middleware.

:class:`BearerTokenMiddleware` is a Starlette middleware that validates the
``Authorization: Bearer <token>`` header on every incoming request.

Behaviour
---------
* If ``auth_token`` is ``None`` the middleware is in **dev mode** and lets
  every request through without checking headers.
* WebSocket upgrade requests are let through here (the actual token check
  happens inside the WebSocket handler after the handshake).
* All other requests without a valid token receive ``401 Unauthorized``.

Usage::

    from openjiuwen.gateway.auth import BearerTokenMiddleware

    app.add_middleware(BearerTokenMiddleware, auth_token="my-secret")
"""

from __future__ import annotations
from typing import Optional

import json

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp


class BearerTokenMiddleware(BaseHTTPMiddleware):
    """Validate ``Authorization: Bearer <token>`` on every HTTP request.

    Args:
        app:        The ASGI application to wrap.
        auth_token: Expected bearer token.  ``None`` → auth disabled.
    """

    def __init__(self, app: ASGIApp, *, auth_token: Optional[str]) -> None:
        super().__init__(app)
        self._token = auth_token

    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        # Dev mode — no auth required.
        if self._token is None:
            return await call_next(request)

        # WebSocket upgrades are let through here; the WS handler performs its
        # own token check inside the connection lifecycle.
        if request.headers.get("upgrade", "").lower() == "websocket":
            return await call_next(request)

        auth = request.headers.get("authorization", "")
        provided = auth[7:] if auth.startswith("Bearer ") else ""

        if not provided or provided != self._token:
            body = json.dumps({"detail": "Unauthorized"})
            return Response(
                content=body,
                status_code=401,
                media_type="application/json",
            )

        return await call_next(request)
