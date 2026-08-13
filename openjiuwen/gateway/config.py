"""Gateway configuration.

:class:`GatewayConfig` is passed to :func:`~openjiuwen.gateway.app.build_gateway_app`
and to the CLI entry point.  It collects every knob you can turn on the gateway
without touching code.

Example::

    from openjiuwen.gateway import GatewayConfig, AgentSpec
    from openjiuwen.sdk import ModelConfig

    config = GatewayConfig(
        auth_token="my-secret",
        agents=[
            AgentSpec(
                id="researcher",
                name="Researcher",
                model=ModelConfig.from_env(),
            ),
        ],
    )
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Optional

if TYPE_CHECKING:
    from openjiuwen.sdk.core.config import ModelConfig
    from openjiuwen.sdk.core.tools import SdkTool


@dataclass
class AgentSpec:
    """Static description of one agent exposed by the gateway.

    Args:
        id:            Unique identifier used in REST/WS paths (e.g. ``"researcher"``).
        name:          Human-readable name forwarded to the agent runtime.
        model:         :class:`~openjiuwen.sdk.core.config.ModelConfig` for in-process agents.
                       Required when the gateway runs agents in-process; may be ``None``
                       for gateways that proxy to an upstream agent server.
        tools:         Tool list registered with the agent.
        system_prompt: Override the default system prompt.
        meta:          Arbitrary extra metadata (tags, description, …) returned by
                       ``GET /v1/agents/{id}``.
    """

    id: str
    name: str
    model: "ModelConfig | None" = None
    tools: "list[SdkTool]" = field(default_factory=list)
    system_prompt: Optional[str] = None
    meta: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-safe dict (for REST responses)."""
        return {
            "id": self.id,
            "name": self.name,
            "model": {
                "provider": self.model.provider,
                "model": self.model.model,
            } if self.model is not None else None,
            "tools": [t.name for t in self.tools],
            "system_prompt": self.system_prompt,
            **self.meta,
        }


@dataclass
class GatewayConfig:
    """Top-level gateway configuration.

    Args:
        auth_token:       Bearer token required on every REST/WS request.
                          ``None`` disables authentication (development mode).
                          Can also be set via the ``JIUWENSWARM_GATEWAY_TOKEN``
                          env var.
        agents:           Pre-registered :class:`AgentSpec` list.
        checkpoint_store: Name of a registered checkpoint backend
                          (e.g. ``"sqlite"``, ``"s3"``).  Used by the
                          ``/v1/checkpoints`` endpoints.
        host:             Bind host (default ``"0.0.0.0"``).
        port_rest:        HTTP REST port (default ``19001``).
        port_ws:          WebSocket port (default ``19000``).
                          If equal to ``port_rest``, both are served on one port.
    """

    auth_token: Optional[str] = field(
        default_factory=lambda: os.environ.get("JIUWENSWARM_GATEWAY_TOKEN")
    )
    agents: list[AgentSpec] = field(default_factory=list)
    checkpoint_store: Optional[str] = None
    host: str = "0.0.0.0"
    port_rest: int = 19001
    port_ws: int = 19000

    @classmethod
    def from_env(cls) -> "GatewayConfig":
        """Build a :class:`GatewayConfig` from environment variables.

        Reads ``JIUWENSWARM_GATEWAY_TOKEN`` for the auth token.  All other
        settings use defaults.
        """
        return cls()
