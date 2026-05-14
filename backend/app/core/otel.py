"""OpenTelemetry initializer (S4-H).

Opt-in: when `OTEL_EXPORTER_OTLP_ENDPOINT` is set, this configures
tracer + meter providers that export to the configured collector
(Tempo, Honeycomb, Datadog OTel, etc.). When unset, the call is a no-op
so dev installs don't need an OTel collector to boot.
"""

from __future__ import annotations

import logging
import os

log = logging.getLogger(__name__)


def init_otel(service_name: str = "dclaw-backend") -> None:
    endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
    if not endpoint:
        return
    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
    except Exception:  # pragma: no cover — otel libs optional
        log.warning("opentelemetry libs not installed; tracing disabled")
        return

    resource = Resource.create({"service.name": service_name})
    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
    trace.set_tracer_provider(provider)
    log.info("opentelemetry initialised → %s", endpoint)


def sentry_tag(key: str, value: str) -> None:
    """Attach a Sentry tag without requiring the SDK to be installed.

    Used by request middleware + agent runtime to enrich error reports
    with `organization_id`, `agent`, `capability`, etc.
    """
    try:
        import sentry_sdk

        sentry_sdk.set_tag(key, value)
    except Exception:  # pragma: no cover
        pass
