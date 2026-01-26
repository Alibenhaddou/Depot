from __future__ import annotations

from collections.abc import Awaitable, Callable
import os
from pathlib import Path
import time

from fastapi import FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles

from .routes.auth import router as auth_router
from .routes.auth_ui import router as auth_ui_router
from .routes.jira import router as jira_router
from .routes.ai import router as ai_router
from .routes.ui import router as ui_router  # version "choix 2" => prefix="/ui"
from .routes.po import router as po_router
from .routes.debug import router as debug_router
from .routes.po import router as po_router
from fastapi.responses import RedirectResponse
from prometheus_client import (
    generate_latest,
    CONTENT_TYPE_LATEST,
    Counter,
    Histogram,
    CollectorRegistry,
)

import platform

from app.core.telemetry import setup_telemetry


def _env_flag(name: str, default: bool = False) -> bool:
    """Return a boolean flag from environment variables.

    Interprets common truthy values (1, true, yes, y, on) in a case-insensitive
    way and falls back to `default` if the env var is not present.
    """
    v = os.getenv(name)
    if v is None:
        return default
    return v.strip().lower() in {"1", "true", "yes", "y", "on"}


def create_app() -> FastAPI:
    app = FastAPI(title="CT - Delivery Assistant (POC)", version="0.1.0")

    @app.get("/version", include_in_schema=False)
    async def version() -> dict:
        # Minimal endpoint used by tests/observability.
        try:
            version_str = (Path(__file__).resolve().parents[2] / "VERSION").read_text().strip()
        except Exception:
            version_str = app.version
        return {
            "service": "api",
            "version": version_str,
            "python_version": platform.python_version(),
            "build_date": time.strftime("%Y-%m-%d"),
        }

    registry = CollectorRegistry()

    REQUEST_COUNT = Counter(
        "http_requests_total",
        "Total HTTP requests",
        ["method", "path", "status"],
        registry=registry,
    )
    REQUEST_LATENCY = Histogram(
        "http_request_duration_seconds",
        "HTTP request latency in seconds",
        ["method", "path"],
        registry=registry,
    )

    @app.middleware("http")
    async def metrics_middleware(
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - start
        REQUEST_COUNT.labels(
            request.method, request.url.path, str(response.status_code)
        ).inc()
        REQUEST_LATENCY.labels(request.method, request.url.path).observe(elapsed)
        return response

    @app.get("/metrics", include_in_schema=False)
    async def metrics() -> Response:
        data = generate_latest(registry)
        return Response(content=data, media_type=CONTENT_TYPE_LATEST)

    @app.get("/", include_in_schema=False)
    async def root() -> RedirectResponse:
        return RedirectResponse("/ui")

    app_dir = Path(__file__).resolve().parent

    # Static assets (séparation maximale)
    app.mount(
        "/auth/assets",
        StaticFiles(directory=app_dir / "ui" / "auth"),
        name="auth-assets",
    )
    app.mount(
        "/ui/assets",
        StaticFiles(directory=app_dir / "ui" / "poc"),
        name="ui-assets",
    )

    # OAuth Atlassian (login/callback/logout)
    app.include_router(auth_router)

    # UI login indépendante (/auth)
    app.include_router(auth_ui_router)

    # Jira endpoints (issue/search/select/instances)
    app.include_router(jira_router)

    # AI endpoints
    app.include_router(ai_router)

    # PO projects endpoints
    app.include_router(po_router)

    # UI POC (choix 2) : idéalement en dev seulement
    enable_poc = _env_flag("ENABLE_POC_UI", default=True)
    if enable_poc:
        app.include_router(ui_router)

    # Debug endpoints : dev only
    enable_debug = _env_flag("ENABLE_DEBUG_ROUTES", default=False)
    if enable_debug:
        app.include_router(debug_router)

    # OpenTelemetry (optional)
    setup_telemetry(app, service_name="ct-delivery-assistant")

    return app


app = create_app()
