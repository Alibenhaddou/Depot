from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel

from app.auth.session_store import ensure_session
from app.core.redis import get_session

router = APIRouter(prefix="/ui", tags=["ui"])

_APP_DIR = Path(__file__).resolve().parents[1]
_UI_DIR = _APP_DIR / "ui" / "poc"
_HTML = (_UI_DIR / "poc.html").read_text(encoding="utf-8")


class UiState(BaseModel):  # type: ignore[misc]
    logged_in: bool
    login_url: str = "/login"
    logout_url: str = "/logout"
    show_debug_links: bool = False  # piloté par config ensuite


@router.get("", response_class=HTMLResponse)
async def ui_page(request: Request) -> HTMLResponse:
    resp = HTMLResponse(_HTML)
    sid = ensure_session(request, resp)
    session = get_session(sid) or {}
    if not session.get("access_token"):
        redirect = RedirectResponse("/auth")
        ensure_session(request, redirect)
        return redirect
    return resp


@router.get("/state", response_model=UiState)
async def ui_state(request: Request, response: Response) -> UiState:
    sid = ensure_session(request, response)
    session = get_session(sid) or {}
    logged_in = bool(session.get("access_token"))

    # TODO: remplacer par settings/env
    show_debug = False

    return UiState(
        logged_in=logged_in,
        show_debug_links=show_debug,
    )
