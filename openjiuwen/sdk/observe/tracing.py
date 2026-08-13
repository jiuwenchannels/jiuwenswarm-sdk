"""SDK Observability façade — OpenTelemetry tracing for agents and workflows.

Call :func:`init_otel_tracer` once at application startup to instrument all
subsequent :meth:`~openjiuwen.sdk.core.agent.Agent.run` and
:meth:`~openjiuwen.sdk.core.agent.Agent.stream` calls with OpenTelemetry spans.

Quick start::

    from openjiuwen.sdk.observe.tracing import init_otel_tracer, OtelTracerConfig

    init_otel_tracer(OtelTracerConfig(
        endpoint="http://localhost:4317",
        service_name="my-agent-service",
    ))
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OtelTracerConfig:
    """Configuration for the OpenTelemetry tracer.

    Attributes:
        endpoint:            OTLP gRPC collector endpoint (e.g. ``"http://localhost:4317"``).
        service_name:        Service name as it appears in your tracing backend.
        sample_rate:         Fraction of traces to record, in [0, 1].
        redact_llm_content:  Strip LLM prompt/response text from spans (for PII compliance).
        resource_attributes: Extra resource attributes attached to every span.
        headers:             HTTP headers for authenticated OTLP exporters.
    """

    endpoint: str = "http://localhost:4317"
    service_name: str = "jiuwenswarm"
    sample_rate: float = 1.0
    redact_llm_content: bool = False
    resource_attributes: dict[str, str] = field(default_factory=dict)
    headers: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# OtelTracer façade
# ---------------------------------------------------------------------------


class OtelTracer:
    """Manages the process-global OpenTelemetry tracer.

    Use :func:`init_otel_tracer` instead of instantiating directly.

    Attributes:
        config: The :class:`OtelTracerConfig` this tracer was created with.
    """

    def __init__(self, config: OtelTracerConfig) -> None:
        self.config = config
        self._provider: Any = None
        self._tracer: Any = None
        self._active = False

    # ------------------------------------------------------------------
    # Instrumentation
    # ------------------------------------------------------------------

    def instrument(self, agent: Any) -> None:
        """Attach OTel spans to every ``run`` and ``stream`` call on *agent*.

        This method wraps the agent's ``run`` and ``stream`` methods to emit
        OpenTelemetry spans.  If the ``opentelemetry-sdk`` package is not
        installed the method logs a warning and does nothing.

        Args:
            agent: A :class:`~openjiuwen.sdk.core.agent.Agent` instance.
        """
        if not self._active:
            log.warning(
                "[tracing] OtelTracer is not active. "
                "Call init_otel_tracer() before instrument()."
            )
            return
        self._wrap_agent(agent)

    def _wrap_agent(self, agent: Any) -> None:
        tracer = self._tracer
        config = self.config

        original_run = agent.run

        async def traced_run(prompt: str, **kwargs: Any) -> Any:
            if tracer is None:
                return await original_run(prompt, **kwargs)
            span_name = f"agent.run:{getattr(agent, '_handle', agent)!r}"[:80]
            with tracer.start_as_current_span(span_name) as span:
                span.set_attribute("agent.prompt_length", len(prompt))
                if not config.redact_llm_content:
                    span.set_attribute("agent.prompt", prompt[:512])
                result = await original_run(prompt, **kwargs)
                if hasattr(result, "session_id") and result.session_id:
                    span.set_attribute("agent.session_id", result.session_id)
                return result

        agent.run = traced_run  # type: ignore[method-assign]

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def _init(self) -> None:
        """Initialise the OTLP exporter and tracer provider."""
        try:
            from opentelemetry import trace
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

            resource_attrs = {
                "service.name": self.config.service_name,
                **self.config.resource_attributes,
            }
            resource = Resource.create(resource_attrs)
            sampler = TraceIdRatioBased(self.config.sample_rate)
            provider = TracerProvider(resource=resource, sampler=sampler)
            exporter = OTLPSpanExporter(
                endpoint=self.config.endpoint,
                headers=self.config.headers,
            )
            provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(provider)
            self._provider = provider
            self._tracer = provider.get_tracer("openjiuwen.sdk")
            self._active = True
            log.info(
                "[tracing] OpenTelemetry tracer initialised. endpoint=%s service=%s",
                self.config.endpoint,
                self.config.service_name,
            )
        except ImportError:
            log.warning(
                "[tracing] opentelemetry-sdk is not installed. "
                "Install it with: pip install openjiuwen-sdk[otel]. "
                "Tracing is disabled."
            )

    def shutdown(self) -> None:
        """Flush and shut down the tracer provider."""
        if self._provider is not None and hasattr(self._provider, "shutdown"):
            self._provider.shutdown()
            self._active = False

    def __repr__(self) -> str:
        return (
            f"OtelTracer(service={self.config.service_name!r}, "
            f"active={self._active})"
        )


# ---------------------------------------------------------------------------
# Module-level API
# ---------------------------------------------------------------------------

_global_tracer: OtelTracer | None = None


def init_otel_tracer(config: OtelTracerConfig | None = None) -> OtelTracer:
    """Initialise the process-global OpenTelemetry tracer.

    Call this once at application startup.  All subsequent agent/workflow
    invocations will emit spans automatically.

    Args:
        config: :class:`OtelTracerConfig` (uses defaults if omitted).

    Returns:
        The initialised :class:`OtelTracer`.
    """
    global _global_tracer  # noqa: PLW0603

    if config is None:
        config = OtelTracerConfig()

    tracer = OtelTracer(config)
    tracer._init()
    _global_tracer = tracer
    return tracer


def get_tracer() -> OtelTracer | None:
    """Return the active global :class:`OtelTracer`, or ``None``."""
    return _global_tracer
