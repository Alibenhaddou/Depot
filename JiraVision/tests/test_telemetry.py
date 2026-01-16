import types
import sys

from fastapi import FastAPI

from app.core.telemetry import setup_telemetry


def _install_fake_otel():
    trace_mod = types.ModuleType("opentelemetry.trace")
    def set_tracer_provider(provider):
        trace_mod.provider = provider
    trace_mod.set_tracer_provider = set_tracer_provider

    sdk_resources = types.ModuleType("opentelemetry.sdk.resources")
    class Resource:
        @staticmethod
        def create(attrs):
            return attrs
    sdk_resources.Resource = Resource

    sdk_trace = types.ModuleType("opentelemetry.sdk.trace")
    class TracerProvider:
        def __init__(self, resource=None):
            self.resource = resource
            self.processor = None
        def add_span_processor(self, processor):
            self.processor = processor
    sdk_trace.TracerProvider = TracerProvider

    sdk_export = types.ModuleType("opentelemetry.sdk.trace.export")
    class BatchSpanProcessor:
        def __init__(self, exporter):
            self.exporter = exporter
    sdk_export.BatchSpanProcessor = BatchSpanProcessor

    exporter_mod = types.ModuleType("opentelemetry.exporter.otlp.proto.http.trace_exporter")
    class OTLPSpanExporter:
        def __init__(self, endpoint=None):
            self.endpoint = endpoint
    exporter_mod.OTLPSpanExporter = OTLPSpanExporter

    inst_fastapi = types.ModuleType("opentelemetry.instrumentation.fastapi")
    class FastAPIInstrumentor:
        @staticmethod
        def instrument_app(app):
            app.state.otel_instrumented = True
    inst_fastapi.FastAPIInstrumentor = FastAPIInstrumentor

    inst_httpx = types.ModuleType("opentelemetry.instrumentation.httpx")
    class HTTPXClientInstrumentor:
        def instrument(self):
            self.instrumented = True
    inst_httpx.HTTPXClientInstrumentor = HTTPXClientInstrumentor

    sys.modules["opentelemetry"] = types.ModuleType("opentelemetry")
    sys.modules["opentelemetry.trace"] = trace_mod
    sys.modules["opentelemetry.sdk"] = types.ModuleType("opentelemetry.sdk")
    sys.modules["opentelemetry.sdk.resources"] = sdk_resources
    sys.modules["opentelemetry.sdk.trace"] = sdk_trace
    sys.modules["opentelemetry.sdk.trace.export"] = sdk_export
    sys.modules["opentelemetry.exporter"] = types.ModuleType("opentelemetry.exporter")
    sys.modules["opentelemetry.exporter.otlp"] = types.ModuleType("opentelemetry.exporter.otlp")
    sys.modules["opentelemetry.exporter.otlp.proto"] = types.ModuleType("opentelemetry.exporter.otlp.proto")
    sys.modules["opentelemetry.exporter.otlp.proto.http"] = types.ModuleType("opentelemetry.exporter.otlp.proto.http")
    sys.modules["opentelemetry.exporter.otlp.proto.http.trace_exporter"] = exporter_mod
    sys.modules["opentelemetry.instrumentation"] = types.ModuleType("opentelemetry.instrumentation")
    sys.modules["opentelemetry.instrumentation.fastapi"] = inst_fastapi
    sys.modules["opentelemetry.instrumentation.httpx"] = inst_httpx


def test_setup_telemetry_no_endpoint(monkeypatch):
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    app = FastAPI()
    setup_telemetry(app, "svc")
    assert not hasattr(app.state, "otel_instrumented")


def test_setup_telemetry_enabled(monkeypatch):
    _install_fake_otel()
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel")
    app = FastAPI()
    setup_telemetry(app, "svc")
    assert app.state.otel_instrumented is True


def test_setup_telemetry_import_error(monkeypatch):
    # Force import error to cover exception branch
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel")
    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("opentelemetry"):
            raise ImportError("boom")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    app = FastAPI()
    setup_telemetry(app, "svc")
    assert not hasattr(app.state, "otel_instrumented")
