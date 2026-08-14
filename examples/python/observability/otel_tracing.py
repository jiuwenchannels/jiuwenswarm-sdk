"""11_observability.py — OpenTelemetry tracing for agents and workflows.

Corresponds to §11 of the usage examples.

Shows:
  - init_otel_tracer() with OTLP gRPC collector endpoint
  - OtelTracerConfig options: service_name, sample_rate, redact_llm_content
  - Automatic span creation for all subsequent agent/workflow calls

Run:
    python examples/11_observability.py

Prerequisites:
    An OTLP-compatible collector must be running (e.g., Jaeger all-in-one,
    Grafana Tempo, or the OpenTelemetry Collector) on localhost:4317.
"""

from openjiuwen.sdk.tracing import init_otel_tracer, OtelTracerConfig
from openjiuwen.sdk import Agent, ModelConfig

# Call once at application startup
init_otel_tracer(OtelTracerConfig(
    endpoint="http://localhost:4317",   # OTLP gRPC collector
    service_name="my-agent-service",
    sample_rate=1.0,
    redact_llm_content=False,           # set True in production
))


# All subsequent agent/workflow calls emit spans automatically
async def main():
    import asyncio
    agent = await Agent.create("traced-agent", model=ModelConfig.from_env())
    result = await agent.run("Explain tracing in one sentence.")
    print(result.text)
    # Spans appear in your OTel backend (Jaeger, Tempo, Datadog, …)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
