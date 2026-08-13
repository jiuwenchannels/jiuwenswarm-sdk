"""30_gateway_startup.py — HTTP + WebSocket gateway.

Demonstrate how to:
  1. Build a GatewayConfig and start the REST server with uvicorn.
  2. Query it with httpx (REST) and websockets (WebSocket).

Prerequisites
-------------
    pip install openjiuwen-sdk[gateway] httpx websockets

Run
---
    python examples/python/30_gateway_startup.py
"""

from __future__ import annotations

import asyncio
import json
import threading

import httpx

BASE_REST = "http://localhost:19001"
BASE_WS = "ws://localhost:19000/v1/ws"


# ---------------------------------------------------------------------------
# 1. Start the gateway in a background thread
# ---------------------------------------------------------------------------


def _start_server() -> None:
    """Build and serve the gateway (blocks until process exits)."""
    import uvicorn

    from openjiuwen.gateway import GatewayConfig, build_gateway_app
    from openjiuwen.gateway.config import AgentSpec
    from openjiuwen.sdk.core.config import ModelConfig

    spec = AgentSpec(
        id="assistant",
        name="Assistant",
        model=ModelConfig(provider="openai", model="gpt-4o"),
    )
    config = GatewayConfig(
        auth_token=None,          # dev mode — no auth required
        agents=[spec],
        host="127.0.0.1",
        port_rest=19001,
        port_ws=19000,
    )
    app = build_gateway_app(config)
    uvicorn.run(app, host=config.host, port=config.port_rest, log_level="warning")


# ---------------------------------------------------------------------------
# 2. REST examples
# ---------------------------------------------------------------------------


async def demo_rest() -> None:
    async with httpx.AsyncClient(base_url=BASE_REST) as client:
        # Health check
        r = await client.get("/v1/health")
        print("Health:", r.json())

        # List agents
        r = await client.get("/v1/agents")
        print("Agents:", [a["id"] for a in r.json()["agents"]])

        # Create a session
        r = await client.post(
            "/v1/sessions",
            json={"title": "demo", "agent_id": "assistant"},
        )
        session_id = r.json()["session"]["id"]
        print("Session created:", session_id)

        # Blocking chat
        r = await client.post(
            f"/v1/sessions/{session_id}/chat",
            json={"message": "What is 2 + 2?"},
        )
        print("Chat response:", r.json().get("response", r.text))

        # SSE streaming chat
        print("Streaming: ", end="", flush=True)
        async with client.stream(
            "POST",
            f"/v1/sessions/{session_id}/chat/stream",
            json={"message": "Count from 1 to 5."},
        ) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data:"):
                    token = line[5:].strip()
                    if token and token != "[DONE]":
                        print(token, end="", flush=True)
        print()


# ---------------------------------------------------------------------------
# 3. WebSocket example
# ---------------------------------------------------------------------------


async def demo_ws() -> None:
    try:
        import websockets  # type: ignore[import]
    except ImportError:
        print("[ws] install 'websockets' to run the WebSocket demo")
        return

    async with websockets.connect(BASE_WS) as ws:  # type: ignore[attr-defined]
        # Identify
        await ws.send(json.dumps({"type": "connect", "client_type": "python"}))
        ack = json.loads(await ws.recv())
        print("WS ack:", ack)

        # Create session
        await ws.send(json.dumps({
            "type": "create_session",
            "agent_id": "assistant",
            "title": "WS demo",
        }))
        created = json.loads(await ws.recv())
        print("WS session:", created["session"]["id"])

        # Chat (stream)
        await ws.send(json.dumps({"type": "chat", "message": "Say hello."}))
        print("WS stream: ", end="", flush=True)
        async for raw in ws:
            msg = json.loads(raw)
            if msg["type"] == "token":
                print(msg["text"], end="", flush=True)
            elif msg["type"] in ("done", "error"):
                break
        print()


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


async def main() -> None:
    # Launch gateway in background thread
    t = threading.Thread(target=_start_server, daemon=True)
    t.start()

    # Give uvicorn a moment to bind
    await asyncio.sleep(1.5)

    print("=== REST demo ===")
    await demo_rest()

    print("\n=== WebSocket demo ===")
    await demo_ws()


if __name__ == "__main__":
    asyncio.run(main())
