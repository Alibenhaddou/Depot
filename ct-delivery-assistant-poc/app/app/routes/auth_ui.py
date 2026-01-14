from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request, Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from app.auth.session_store import ensure_session
from app.core.redis import get_session

router = APIRouter(prefix="/auth", tags=["ui-auth"])

_APP_DIR = Path(__file__).resolve().parents[1]  # .../app
_UI_DIR = _APP_DIR / "ui" / "auth"
_HTML_PATH = _UI_DIR / "auth.html"

_HTML = _HTML_PATH.read_text(encoding="utf-8")  # cache en mémoire


class AuthState(BaseModel):  # type: ignore[misc]
    logged_in: bool
    login_url: str = "/login"
    logout_url: str = "/logout"


@router.get("", response_class=HTMLResponse)
async def auth_page(request: Request) -> HTMLResponse:
    resp = HTMLResponse(_HTML)
    ensure_session(request, resp)
    return resp


@router.get("/state", response_model=AuthState)
async def auth_state(request: Request, response: Response) -> AuthState:
    sid = ensure_session(request, response)
    session = get_session(sid) or {}
    return AuthState(logged_in=bool(session.get("access_token")))
