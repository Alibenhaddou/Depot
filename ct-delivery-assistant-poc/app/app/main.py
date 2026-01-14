from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routes.auth import router as auth_router
from app.routes.auth_ui import router as auth_ui_router
from app.routes.jira import router as jira_router
from app.routes.ai import router as ai_router
from app.routes.ui import router as ui_router  # version "choix 2" => prefix="/ui"
from app.routes.debug import router as debug_router
from fastapi.responses import RedirectResponse


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

    # UI POC (choix 2) : idéalement en dev seulement
    enable_poc = _env_flag("ENABLE_POC_UI", default=True)
    if enable_poc:
        app.include_router(ui_router)

    # Debug endpoints : dev only
    enable_debug = _env_flag("ENABLE_DEBUG_ROUTES", default=False)
    if enable_debug:
        app.include_router(debug_router)

    return app


app = create_app()
