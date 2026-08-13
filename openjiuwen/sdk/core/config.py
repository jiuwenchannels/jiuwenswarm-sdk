"""
SDK configuration — two dataclasses matching the two execution modes.

ModelConfig  — in-process mode (Agent.create).  No server URL.
RemoteConfig — remote mode    (Agent.connect).  No LLM credentials.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Provider name normalisation
# The underlying runtime uses capitalised provider names ("OpenAI", "Anthropic").
# The SDK accepts lowercase for developer convenience.
# ---------------------------------------------------------------------------

_PROVIDER_MAP: dict[str, str] = {
    "openai": "OpenAI",
    "anthropic": "Anthropic",
    "siliconflow": "SiliconFlow",
    "deepseek": "DeepSeek",
    "dashscope": "DashScope",
    "openrouter": "OpenRouter",
    "vllm": "OpenAI",          # vLLM exposes an OpenAI-compatible API
}


def _normalise_provider(provider: str) -> str:
    return _PROVIDER_MAP.get(provider.lower(), provider)


# ---------------------------------------------------------------------------
# ModelConfig — in-process execution
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ModelConfig:
    """Configuration for :meth:`Agent.create` (in-process runtime).

    The agent runtime (``openjiuwen.core``, ``openjiuwen.harness``) executes
    inside the caller's Python process.  No JiuwenSwarm server is needed.

    Args:
        provider:    LLM provider name.  Accepted values (case-insensitive):
                     ``"openai"``, ``"anthropic"``, ``"siliconflow"``,
                     ``"deepseek"``, ``"dashscope"``, ``"openrouter"``,
                     ``"vllm"``.
        model:       Model identifier (e.g. ``"gpt-4o"``, ``"claude-3-5-sonnet-20241022"``).
        api_key:     Provider API key.  Falls back to the ``OPENAI_API_KEY``
                     / ``ANTHROPIC_API_KEY`` / ``JIUWENSWARM_API_KEY``
                     environment variables.
        api_base:    Override the provider base URL (e.g. for local vLLM).
        temperature: Sampling temperature.
        max_tokens:  Maximum tokens to generate.
        timeout:     Per-request timeout in seconds.
        max_retries: Number of retries on transient errors.
    """

    provider: str = "openai"
    model: str = "gpt-4o"
    api_key: str | None = None
    api_base: str | None = None
    temperature: float | None = None
    max_tokens: int | None = None
    timeout: float = 60.0
    max_retries: int = 3

    # ------------------------------------------------------------------
    # Internal helpers (not part of public contract)
    # ------------------------------------------------------------------

    @property
    def _normalised_provider(self) -> str:
        return _normalise_provider(self.provider)

    @classmethod
    def from_env(cls) -> "ModelConfig":
        """Build a :class:`ModelConfig` from environment variables.

        Reads:

        - ``JIUWENSWARM_PROVIDER`` (default: ``"openai"``)
        - ``JIUWENSWARM_MODEL`` (default: ``"gpt-4o"``)
        - ``JIUWENSWARM_API_KEY`` → ``OPENAI_API_KEY`` → ``ANTHROPIC_API_KEY``
        - ``JIUWENSWARM_API_BASE``
        - ``JIUWENSWARM_TEMPERATURE``
        - ``JIUWENSWARM_MAX_TOKENS``
        """
        api_key = (
            os.environ.get("JIUWENSWARM_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("ANTHROPIC_API_KEY")
        )
        temperature_raw = os.environ.get("JIUWENSWARM_TEMPERATURE")
        max_tokens_raw = os.environ.get("JIUWENSWARM_MAX_TOKENS")
        return cls(
            provider=os.environ.get("JIUWENSWARM_PROVIDER", "openai"),
            model=os.environ.get("JIUWENSWARM_MODEL", "gpt-4o"),
            api_key=api_key or None,
            api_base=os.environ.get("JIUWENSWARM_API_BASE") or None,
            temperature=float(temperature_raw) if temperature_raw else None,
            max_tokens=int(max_tokens_raw) if max_tokens_raw else None,
        )


# ---------------------------------------------------------------------------
# RemoteConfig — remote client execution
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RemoteConfig:
    """Configuration for :meth:`Agent.connect` (remote client mode).

    The SDK connects to a running JiuwenSwarm server over WebSocket or REST.
    The server manages the runtime and LLM credentials; no model API keys are
    needed on the client side.

    This is exactly what the JiuwenSwarm browser extension and mobile app do
    — now available from Python.

    Args:
        server_url:  WebSocket (``ws://``) or REST (``http://``) URL of the
                     JiuwenSwarm gateway.  Defaults to localhost.
        auth_token:  Bearer token for the gateway ``Authorization`` header.
        timeout:     Request / message timeout in seconds.
        max_retries: Number of reconnection attempts before giving up.
    """

    server_url: str = "ws://localhost:19000/v1/ws"
    auth_token: str | None = None
    timeout: float = 60.0
    max_retries: int = 3

    @classmethod
    def from_env(cls) -> "RemoteConfig":
        """Build a :class:`RemoteConfig` from environment variables.

        Reads:

        - ``JIUWENSWARM_URL`` (WebSocket or HTTP base URL)
        - ``JIUWENSWARM_TOKEN``
        """
        return cls(
            server_url=os.environ.get(
                "JIUWENSWARM_URL", "ws://localhost:19000/v1/ws"
            ),
            auth_token=os.environ.get("JIUWENSWARM_TOKEN") or None,
        )
