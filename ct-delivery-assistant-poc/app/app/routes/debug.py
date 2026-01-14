"""
app/routes/debug.py

Endpoints de debug (dev only).
But : vérifier cookies, session Redis et état Jira (multi-instance).
Ces routes ne font pas d'appels externes.
"""

from __future__ import annotations

import hashlib
import os
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request

from app.auth.session_store import get_sid
from app.core.redis import get_session

router = APIRouter(prefix="/debug", tags=["debug"])


def _enabled() -> bool:
    v = os.getenv("ENABLE_DEBUG_ROUTES", "").strip().lower()
    return v in {"1", "true", "yes", "y", "on"}


def _require_enabled() -> None:
    if not _enabled():
        # 404 plutôt que 403 => moins “bruyant” (security by minimization)
        raise HTTPException(status_code=404, detail="Not found")


def _fingerprint(value: str) -> str:
    # Fingerprint non réversible (utile pour corréler sans fuite)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


@router.get("/cookie")
async def debug_cookie(request: Request) -> Dict[str, Any]:
    _require_enabled()

    raw = request.cookies.get("sid")
    sid = get_sid(request)
    session = get_session(sid) if sid else None

    tbc = (session or {}).get("tokens_by_cloud") or {}
    has_token = bool((session or {}).get("access_token")) or bool(tbc)

    return {
        "sid_cookie_present": bool(raw),
        "sid_fingerprint": _fingerprint(sid) if sid else None,
        "redis_session_present": bool(session),
        "has_access_token": has_token,
        "oauth_state_cookie_present": bool(request.cookies.get("oauth_state")),
    }


@router.get("/session")
async def debug_session(request: Request) -> Dict[str, Any]:
    _require_enabled()

    sid = get_sid(request)
    if not sid:
        raise HTTPException(401, "Pas de cookie sid")

    session = get_session(sid)
    if not session:
        raise HTTPException(401, "Pas de session Redis")

    tokens_by_cloud = session.get("tokens_by_cloud") or {}
    jira_sites = session.get("jira_sites") or []

    # Sanitize jira_sites: ne pas renvoyer l'objet brut
    safe_sites = []
    for s in jira_sites:
        if not isinstance(s, dict):
            continue
        safe_sites.append({
            "id": s.get("id"),
            "name": s.get("name"),
            "url": s.get("url"),  # keep URL but avoid leaking full object
        })

    return {
        "sid_fingerprint": _fingerprint(sid),
        "has_access_token": bool(session.get("access_token")) or bool(tokens_by_cloud),
        "tokens_by_cloud_keys": list(tokens_by_cloud.keys()),
        "cloud_ids": session.get("cloud_ids"),
        "active_cloud_id": session.get("active_cloud_id"),
        "jira_sites": safe_sites,
        "site_url": session.get("site_url"),
        "scopes": session.get("scopes"),
    }


@router.get("/routes")
async def debug_routes() -> Dict[str, str]:
    _require_enabled()

    return {
        "jira_issue": "/jira/issue",
        "jira_search": "/jira/search",
        "jira_select": "/jira/select",
        "auth_login": "/login",
        "auth_callback": "/oauth/callback",
        "auth_logout": "/logout",
        "debug_cookie": "/debug/cookie",
        "debug_session": "/debug/session",
    }
