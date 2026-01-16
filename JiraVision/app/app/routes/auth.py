from __future__ import annotations

import secrets
import time
from typing import Any, Dict, Optional, List, cast
from urllib.parse import urlencode
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from itsdangerous import BadSignature

from app.core.config import settings
from app.core.redis import get_session, set_session
from app.auth.session_store import ensure_session, destroy_session, state_serializer
from app.clients.jira import JiraClient
from app.services.project_sync import sync_reporter_projects, get_hidden_projects_state

router = APIRouter(tags=["auth"])

AUTH_BASE = "https://auth.atlassian.com"
AUTHORIZE_URL = f"{AUTH_BASE}/authorize"
TOKEN_URL = f"{AUTH_BASE}/oauth/token"
ACCESSIBLE_RESOURCES_URL = "https://api.atlassian.com/oauth/token/accessible-resources"

POST_LOGIN_REDIRECT = "/ui"
POST_LOGOUT_REDIRECT = "/auth"
OAUTH_STATE_MAX_AGE = 60 * 10  # 10 minutes


def _redirect_uri(request: Request) -> str:
    """Retourne l'URI de redirection à utiliser pour OAuth.

    Priorité : variable d'env `ATLASSIAN_REDIRECT_URI` si définie, sinon construction
    depuis l'objet `request` (utile dans des environnements dynamiques type GitLab).
    """
    if getattr(settings, "atlassian_redirect_uri", None):
        return settings.atlassian_redirect_uri
    # fallback : construire l'URL absolue pour la route `oauth_callback`
    return str(request.url_for("oauth_callback"))


async def _get_accessible_resources(access_token: str) -> Any:
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.get(ACCESSIBLE_RESOURCES_URL, headers=headers)

    # Debug: log status and body (truncated) for diagnosing missing Jira resources
    try:
        txt = r.text
    except Exception:
        txt = "(no body)"
    import logging

    logging.getLogger(__name__).info(
        "Accessible-resources response: status=%s, body=%s", r.status_code, txt[:400]
    )

    if r.status_code >= 400:
        raise HTTPException(502, "Erreur accessible-resources")
    return cast(Any, r.json())


def _pick_jira_resources(resources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    jira = []
    for res in resources:
        scopes = res.get("scopes", []) or []
        if ("read:jira-work" in scopes) or any("jira" in s for s in scopes):
            if res.get("id") and res.get("url"):
                jira.append(res)
    return jira


def _expected_state_from_cookie(request: Request) -> Optional[str]:
    raw = request.cookies.get("oauth_state")
    if not raw:
        return None
    try:
        return cast(Optional[str], state_serializer.loads(raw))
    except BadSignature:
        return None


@router.get("/login")
async def login(request: Request) -> RedirectResponse:
    state = secrets.token_urlsafe(16)

    params = {
        "audience": "api.atlassian.com",
        "client_id": settings.atlassian_client_id,
        "scope": settings.atlassian_scopes,
        "redirect_uri": _redirect_uri(request),
        "response_type": "code",
        "prompt": "consent",
        "state": state,
    }

    url = f"{AUTHORIZE_URL}?{urlencode(params)}"
    resp = RedirectResponse(url)

    sid = ensure_session(request, resp)

    session = get_session(sid) or {}
    session["state"] = state
    set_session(sid, session)

    resp.set_cookie(
        key="oauth_state",
        value=state_serializer.dumps(state),
        httponly=True,
        samesite=settings.cookie_samesite,
        secure=settings.cookie_secure,
        path="/",
        max_age=OAUTH_STATE_MAX_AGE,
    )
    return resp


@router.get("/oauth/callback")
async def oauth_callback(
    request: Request,
    response: Response,
    code: Optional[str] = None,
    state: Optional[str] = None,
) -> RedirectResponse:
    sid = ensure_session(request, response)
    session: Dict[str, Any] = get_session(sid) or {}

    expected_state = session.get("state")
    if not expected_state:
        expected_state = _expected_state_from_cookie(request)

    if not code or not state or not expected_state or state != expected_state:
        raise HTTPException(400, "State invalide ou code manquant")

    payload = {
        "grant_type": "authorization_code",
        "client_id": settings.atlassian_client_id,
        "client_secret": settings.atlassian_client_secret,
        "code": code,
        "redirect_uri": _redirect_uri(request),
    }

    async with httpx.AsyncClient(timeout=30) as client:
        r = await client.post(
            TOKEN_URL,
            json=payload,
            headers={"Accept": "application/json"},
        )

    # Debug logging: status and presence of token (do NOT log the token itself)
    try:
        txt = r.text
    except Exception:
        txt = "(no body)"
    import logging

    logging.getLogger(__name__).info(
        "Token endpoint response: status=%s, body=%s", r.status_code, txt[:200]
    )

    if r.status_code >= 400:
        raise HTTPException(502, "Erreur token Atlassian")

    tok = r.json()
    access_token = tok.get("access_token")
    logging.getLogger(__name__).info("Token endpoint returned access_token=%s", bool(access_token))
    if not access_token:
        raise HTTPException(400, "Réponse token inattendue")

    resources = await _get_accessible_resources(access_token)
    logging.getLogger(__name__).info("Accessible resources count: %s", len(resources))
    jira_resources = _pick_jira_resources(resources)
    logging.getLogger(__name__).info("Jira resources found: %s", [r.get("id") for r in jira_resources])
    if not jira_resources:
        raise HTTPException(400, "Aucune ressource Jira trouvée")

    tokens_by_cloud = session.get("tokens_by_cloud") or {}
    for res in jira_resources:
        cloud_id = res["id"]
        tokens_by_cloud[cloud_id] = {
            "access_token": access_token,
            "site_url": (res.get("url") or "").rstrip("/"),
            "name": res.get("name"),
            "scopes": res.get("scopes", []) or [],
            "updated_at": time.time(),
        }

    session["tokens_by_cloud"] = tokens_by_cloud
    session["cloud_ids"] = list(tokens_by_cloud.keys())
    session["jira_sites"] = [
        {
            "id": cid,
            "name": entry.get("name"),
            "url": entry.get("site_url"),
            "scopes": entry.get("scopes", []) or [],
        }
        for cid, entry in tokens_by_cloud.items()
    ]

    active = session.get("active_cloud_id")
    if (not active) or (active not in session["cloud_ids"]):
        session["active_cloud_id"] = session["cloud_ids"][0]

    active_cid = session["active_cloud_id"]
    active_entry = session["tokens_by_cloud"][active_cid]

    # compat / confort (à garder tant que le reste du code l'utilise)
    session["access_token"] = active_entry["access_token"]
    session["site_url"] = active_entry["site_url"]
    session["scopes"] = active_entry.get("scopes", [])

    session.pop("state", None)
    set_session(sid, session)

    import logging
    logging.getLogger(__name__).info("Session after token exchange for sid=%s: %s", sid, session)

    # Auto-sync reporter projects on login
    try:
        clients = []
        for cloud_id in session["cloud_ids"]:
            entry = tokens_by_cloud.get(cloud_id)
            if entry and entry.get("access_token"):
                client = JiraClient(
                    access_token=entry["access_token"],
                    cloud_id=cloud_id,
                )
                clients.append((cloud_id, client))
        
        if clients:
            hidden = get_hidden_projects_state(session)
            projects = await sync_reporter_projects(clients, hidden)
            
            # Filter out hidden projects
            visible_projects = [
                p for p in projects 
                if p.visibility.value == "visible"
            ]
            
            # Store in session
            session["reporter_projects"] = [p.model_dump() for p in visible_projects]
            session["reporter_projects_sync_at"] = datetime.now(timezone.utc).isoformat()
            set_session(sid, session)
            
            # Close all clients
            for _, client in clients:
                await client.aclose()
                
            logging.getLogger(__name__).info(
                "Auto-synced %d reporter projects for sid=%s", 
                len(visible_projects), sid
            )
    except Exception as e:
        # Don't fail login if project sync fails
        logging.getLogger(__name__).warning(
            "Failed to auto-sync reporter projects: %s", e, exc_info=True
        )

    resp = RedirectResponse(url=POST_LOGIN_REDIRECT)
    ensure_session(request, resp)
    # log cookies set on response
    logging.getLogger(__name__).info(
        "Response cookies after login: %s", resp.headers.get("set-cookie")
    )
    resp.delete_cookie("oauth_state", path="/")
    return resp


@router.get("/logout")
async def logout(request: Request) -> RedirectResponse:
    resp = RedirectResponse(POST_LOGOUT_REDIRECT)
    destroy_session(request, resp)
    resp.delete_cookie("oauth_state", path="/")
    return resp
