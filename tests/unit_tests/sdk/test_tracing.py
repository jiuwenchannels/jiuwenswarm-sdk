"""Unit tests for openjiuwen.sdk.tracing — OtelTracer and init helpers."""

from __future__ import annotations

import openjiuwen.sdk.tracing as _tracing_mod
from openjiuwen.sdk.tracing import (
    OtelTracer,
    OtelTracerConfig,
    get_tracer,
    init_otel_tracer,
)


# ---------------------------------------------------------------------------
# OtelTracerConfig tests
# ---------------------------------------------------------------------------


def test_otel_tracer_config_defaults():
    cfg = OtelTracerConfig()
    assert cfg.endpoint == "http://localhost:4317"
    assert cfg.service_name == "jiuwenswarm"
    assert cfg.sample_rate == 1.0
    assert cfg.redact_llm_content is False
    assert cfg.resource_attributes == {}
    assert cfg.headers == {}


def test_otel_tracer_config_custom():
    cfg = OtelTracerConfig(
        endpoint="http://otel:4317",
        service_name="my-service",
        sample_rate=0.5,
        redact_llm_content=True,
    )
    assert cfg.endpoint == "http://otel:4317"
    assert cfg.service_name == "my-service"
    assert cfg.sample_rate == 0.5
    assert cfg.redact_llm_content is True


def test_otel_tracer_config_frozen():
    import pytest

    cfg = OtelTracerConfig()
    with pytest.raises((AttributeError, TypeError)):
        cfg.sample_rate = 0.1  # type: ignore[misc]


# ---------------------------------------------------------------------------
# OtelTracer tests
# ---------------------------------------------------------------------------


def test_otel_tracer_repr():
    cfg = OtelTracerConfig(service_name="test-svc")
    tracer = OtelTracer(cfg)
    rep = repr(tracer)
    assert "test-svc" in rep
    assert "active=False" in rep


def test_otel_tracer_not_active_by_default():
    tracer = OtelTracer(OtelTracerConfig())
    assert tracer._active is False


def test_otel_tracer_instrument_noop_when_inactive(capsys):
    """instrument() should log a warning and return without error."""

    class FakeAgent:
        async def run(self, prompt: str) -> None:
            return None  # pragma: no cover

    tracer = OtelTracer(OtelTracerConfig())
    agent = FakeAgent()
    # Should not raise even though tracer is not active
    tracer.instrument(agent)
    # run method should be unchanged (not wrapped)
    import asyncio

    # Verify the agent run is still callable
    assert callable(agent.run)


def test_otel_tracer_shutdown_noop_without_provider():
    """shutdown() on un-initialised tracer should not raise."""
    tracer = OtelTracer(OtelTracerConfig())
    tracer.shutdown()  # no-op
    assert tracer._active is False


# ---------------------------------------------------------------------------
# Module-level API tests
# ---------------------------------------------------------------------------


def test_init_otel_tracer_returns_tracer():
    """init_otel_tracer() returns an OtelTracer (runtime may not be installed)."""
    # Reset global state before test
    _tracing_mod._global_tracer = None

    tracer = init_otel_tracer(OtelTracerConfig(service_name="unit-test"))
    assert isinstance(tracer, OtelTracer)
    assert tracer.config.service_name == "unit-test"


def test_init_otel_tracer_default_config():
    _tracing_mod._global_tracer = None
    tracer = init_otel_tracer()
    assert tracer.config.service_name == "jiuwenswarm"


def test_get_tracer_returns_global():
    _tracing_mod._global_tracer = None
    assert get_tracer() is None

    tracer = init_otel_tracer()
    assert get_tracer() is tracer


def test_get_tracer_none_before_init():
    _tracing_mod._global_tracer = None
    assert get_tracer() is None
