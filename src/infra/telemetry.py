"""OpenTelemetry instrumentation. Exports traces and metrics via OTLP to the
self-hosted OTel Collector; the service does not know about Grafana/Jaeger/
Prometheus directly - it only speaks OTLP, vendor-neutral."""
from fastapi import FastAPI
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from src.infra.config import get_settings


def setup_telemetry(app: FastAPI) -> None:
    settings = get_settings()
    resource = Resource.create({"service.name": settings.otel_service_name})

    trace_provider = TracerProvider(resource=resource)
    trace_exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_traces_endpoint)
    trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
    trace.set_tracer_provider(trace_provider)

    metric_exporter = OTLPMetricExporter(endpoint=settings.otel_exporter_otlp_metrics_endpoint)
    metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=15000)
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    # Meter provider must be set BEFORE instrument_app so automatic metrics
    # (http.server.duration etc.) are actually collected and exported, in
    # addition to traces.
    FastAPIInstrumentor.instrument_app(app)
