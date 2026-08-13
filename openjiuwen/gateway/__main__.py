"""CLI entry point for the JiuwenSwarm gateway.

Run with::

    python -m openjiuwen.gateway

Or with explicit options::

    python -m openjiuwen.gateway --host 0.0.0.0 --port-rest 19001

Environment variables
---------------------
``JIUWENSWARM_GATEWAY_TOKEN``   Bearer auth token (omit for dev mode / no auth).
``JIUWENSWARM_GATEWAY_HOST``    Bind host (default: ``0.0.0.0``).
``JIUWENSWARM_GATEWAY_PORT``    REST + WS port when running on a single port (default: ``19001``).

All CLI flags override environment variables.
"""

from __future__ import annotations
from typing import Optional

import argparse
import logging
import os
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("openjiuwen.gateway")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m openjiuwen.gateway",
        description="JiuwenSwarm HTTP REST + WebSocket gateway",
    )
    parser.add_argument(
        "--host",
        default=os.environ.get("JIUWENSWARM_GATEWAY_HOST", "0.0.0.0"),
        help="Bind host (default: 0.0.0.0)",
    )
    parser.add_argument(
        "--port-rest",
        type=int,
        default=int(os.environ.get("JIUWENSWARM_GATEWAY_PORT", "19001")),
        dest="port_rest",
        help="REST API port (default: 19001)",
    )
    parser.add_argument(
        "--port-ws",
        type=int,
        default=None,
        dest="port_ws",
        help="WebSocket port. Defaults to --port-rest (single port for both).",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        default=False,
        help="Enable uvicorn auto-reload (development only)",
    )
    parser.add_argument(
        "--log-level",
        default="info",
        choices=["debug", "info", "warning", "error"],
        dest="log_level",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = _parse_args(argv)

    port_ws = args.port_ws if args.port_ws is not None else args.port_rest

    try:
        import uvicorn  # type: ignore[import-untyped]
    except ImportError:
        print(
            "uvicorn is required to run the gateway.\n"
            "Install it with: pip install 'openjiuwen-sdk[gateway]'",
            file=sys.stderr,
        )
        sys.exit(1)

    from openjiuwen.gateway.app import build_gateway_app
    from openjiuwen.gateway.config import GatewayConfig

    config = GatewayConfig.from_env()
    config.host = args.host
    config.port_rest = args.port_rest
    config.port_ws = port_ws

    app = build_gateway_app(config)

    log.info(
        "Starting JiuwenSwarm gateway — REST: http://%s:%d  WS: ws://%s:%d/v1/ws",
        args.host,
        args.port_rest,
        args.host,
        port_ws,
    )

    if args.port_rest == port_ws:
        # Single-port mode: REST + WS on the same port
        uvicorn.run(
            app,
            host=args.host,
            port=args.port_rest,
            log_level=args.log_level,
            reload=args.reload,
        )
    else:
        # Dual-port mode: spin up two uvicorn servers
        import asyncio
        import uvicorn

        async def _serve_both() -> None:
            rest_server = uvicorn.Server(
                uvicorn.Config(app, host=args.host, port=args.port_rest, log_level=args.log_level)
            )
            ws_server = uvicorn.Server(
                uvicorn.Config(app, host=args.host, port=port_ws, log_level=args.log_level)
            )
            await asyncio.gather(rest_server.serve(), ws_server.serve())

        asyncio.run(_serve_both())


if __name__ == "__main__":
    main()
