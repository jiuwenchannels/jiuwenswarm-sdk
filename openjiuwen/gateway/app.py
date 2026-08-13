"""FastAPI application factory.

:func:`build_gateway_app` is the single entry point used by the CLI
(:mod:`openjiuwen.gateway.__main__`) and by tests::

    from openjiuwen.gateway import build_gateway_app, GatewayConfig

    app = build_gateway_app(GatewayConfig(auth_token="secret"))

    # In tests (no real server needed):
    from starlette.testclient import TestClient
    client = TestClient(app)

    # Or with httpx async transport:
    import httpx
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        resp = await ac.get("/v1/health")
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import Response

from openjiuwen.gateway._registry import AgentRegistry, CheckpointStore, SessionStore
from openjiuwen.gateway.auth import BearerTokenMiddleware
from openjiuwen.gateway.config import GatewayConfig
from openjiuwen.gateway.rest import agents, checkpoints, eval, health, knowledge, sessions, tools
from openjiuwen.gateway.ws.router import router as ws_router

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)

API_PREFIX = "/v1"


# ---------------------------------------------------------------------------
# State injection middleware
# ---------------------------------------------------------------------------


async def _inject_state_middleware(request: Request, call_next) -> Response:
    """Copy app-level singletons into per-request state for route handlers."""
    app_state = request.app.state
    request.state.registry = app_state.registry
    request.state.sessions = app_state.sessions
    request.state.checkpoints = app_state.checkpoints
    request.state.knowledge_bases = app_state.knowledge_bases
    return await call_next(request)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def build_gateway_app(config: GatewayConfig | None = None) -> FastAPI:
    """Build and return a fully configured FastAPI gateway application.

    Args:
        config: :class:`~openjiuwen.gateway.config.GatewayConfig` instance.
                Defaults to :meth:`~openjiuwen.gateway.config.GatewayConfig.from_env`.

    Returns:
        A FastAPI application ready to serve REST and WebSocket traffic.
    """
    if config is None:
        config = GatewayConfig.from_env()

    app = FastAPI(
        title="JiuwenSwarm Gateway",
        version="1.0.0",
        description="HTTP REST + WebSocket gateway for the JiuwenSwarm agent runtime.",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # ------------------------------------------------------------------
    # Shared singletons stored on app.state
    # ------------------------------------------------------------------
    app.state.registry = AgentRegistry(config.agents)
    app.state.sessions = SessionStore()
    app.state.checkpoints = CheckpointStore()
    app.state.knowledge_bases: dict = {}
    app.state.auth_token = config.auth_token

    # ------------------------------------------------------------------
    # Middleware (order: outermost first)
    # ------------------------------------------------------------------
    # CORS — permissive defaults; tighten in production via env config
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Bearer-token auth
    app.add_middleware(BearerTokenMiddleware, auth_token=config.auth_token)

    # Inject app-level singletons into each HTTP request's state
    app.middleware("http")(_inject_state_middleware)

    # ------------------------------------------------------------------
    # REST routers
    # ------------------------------------------------------------------
    app.include_router(health.router, prefix=API_PREFIX)
    app.include_router(sessions.router, prefix=API_PREFIX)
    app.include_router(agents.router, prefix=API_PREFIX)
    app.include_router(tools.router, prefix=API_PREFIX)
    app.include_router(knowledge.router, prefix=API_PREFIX)
    app.include_router(eval.router, prefix=API_PREFIX)
    app.include_router(checkpoints.router, prefix=API_PREFIX)

    # ------------------------------------------------------------------
    # WebSocket router
    # ------------------------------------------------------------------
    app.include_router(ws_router, prefix=API_PREFIX)

    return app
