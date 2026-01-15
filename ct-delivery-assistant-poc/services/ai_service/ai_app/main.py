import time

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
from starlette.responses import StreamingResponse
from prometheus_client import (
    generate_latest,
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    CollectorRegistry,
)

from ai_app.routes.ai import router as ai_router
from ai_app.core.telemetry import setup_telemetry

app = FastAPI(title="AI Service (scaffold)", version="0.1.0")

registry = CollectorRegistry()

REQUEST_COUNT = Counter(
    "ai_http_requests_total",
    "Total HTTP requests",
    ["method", "path", "status"],
    registry=registry,
)
REQUEST_LATENCY = Histogram(
    "ai_http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "path"],
    registry=registry,
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    elapsed = time.perf_counter() - start
    REQUEST_COUNT.labels(request.method, request.url.path, str(response.status_code)).inc()
    REQUEST_LATENCY.labels(request.method, request.url.path).observe(elapsed)
    return response

# Health endpoints
@app.get("/health", response_class=PlainTextResponse)
async def health():
    return "ok"

@app.get("/ready", response_class=PlainTextResponse)
async def ready():
    return "ready"

# Metrics (Prometheus)
@app.get("/metrics")
async def metrics():
    data = generate_latest(registry)
    return StreamingResponse(iter([data]), media_type=CONTENT_TYPE_LATEST)

# Include AI routes
app.include_router(ai_router)

# OpenTelemetry (optional)
setup_telemetry(app, service_name="ai-service")
