"""JiuwenSwarm HTTP REST + WebSocket gateway.

The gateway exposes the JiuwenSwarm runtime (or any SDK-compatible agent) over
a standard HTTP / WebSocket API.  It is the server component that browser
extensions, mobile apps, and the TypeScript SDK connect to.

Quick start::

    from openjiuwen.gateway import build_gateway_app, GatewayConfig

    config = GatewayConfig(auth_token="secret")
    app = build_gateway_app(config)
    # Run with: uvicorn openjiuwen.gateway.app:app

CLI::

    python -m openjiuwen.gateway --host 0.0.0.0 --port-rest 19001 --port-ws 19000
"""

from openjiuwen.gateway.app import build_gateway_app
from openjiuwen.gateway.config import AgentSpec, GatewayConfig

__all__ = ["GatewayConfig", "AgentSpec", "build_gateway_app"]
