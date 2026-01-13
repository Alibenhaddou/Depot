from __future__ import annotations

import httpx
from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request, Response

from app.auth.session_store import ensure_session
from app.core.redis import get_session, set_session
from app.clients.jira import JiraClient, select_cloud_id

router = APIRouter(prefix="/jira", tags=["jira"])


def _ensure_sid(request: Request, response: Response) -> str:
    return ensure_session(request, response)


def _require_logged_in(session: Dict[str, Any]) -> None:
    tbc = session.get("tokens_by_cloud") or {}
    if not tbc and "access_token" not in session:
        raise HTTPException(401, "Connecte-toi d'abord via Login Atlassian")

def _map_issue(issue: Dict[str, Any]) -> Dict[str, Any]:
    fields = issue.get("fields", {}) or {}
    return {
        "issue_key": issue.get("key"),
        "summary": fields.get("summary"),
        "status": (fields.get("status") or {}).get("name"),
        "type": (fields.get("issuetype") or {}).get("name"),
        "project": (fields.get("project") or {}).get("key"),
        "assignee": (fields.get("assignee") or {}).get("displayName"),
        "updated": fields.get("updated"),
    }


def _extract_search_items(data: Dict[str, Any]) -> list[Dict[str, Any]]:
    items = data.get("values")
    if items is None:
        items = data.get("issues", [])
    return items or []


def _map_search_result(data: Dict[str, Any]) -> Dict[str, Any]:
    items = _extract_search_items(data)
    issues: list[Dict[str, Any]] = []

    for it in items:
        f = it.get("fields", {}) or {}
        issues.append(
            {
                "key": it.get("key"),
                "summary": f.get("summary"),
                "status": (f.get("status") or {}).get("name"),
                "type": (f.get("issuetype") or {}).get("name"),
                "project": (f.get("project") or {}).get("key"),
                "assignee": (f.get("assignee") or {}).get("displayName"),
                "updated": f.get("updated"),
                "created": f.get("created"),
            }
        )

    return {
        "total": data.get("total"),
        "startAt": data.get("startAt"),
        "maxResults": data.get("maxResults"),
        "returned": len(issues),
        "issues": issues,
    }


def _jira_client_from_session(session: Dict[str, Any], request: Request) -> JiraClient:
    _require_logged_in(session)
    cloud_id = select_cloud_id(session, request)

    tbc = session.get("tokens_by_cloud") or {}
    entry = tbc.get(cloud_id)
    if not entry:
        raise HTTPException(401, "Instance Jira non connectée. Reconnecte-toi via /login.")

    return JiraClient(access_token=entry["access_token"], cloud_id=cloud_id)



@router.post("/select")
async def jira_select(request: Request, response: Response, cloud_id: str) -> Dict[str, Any]:
    sid = _ensure_sid(request, response)
    session = get_session(sid) or {}

    ids = session.get("cloud_ids") or []
    if cloud_id not in ids:
        raise HTTPException(400, "cloud_id inconnu/non connecté")

    session["active_cloud_id"] = cloud_id
    set_session(sid, session)
    return {"ok": True, "active_cloud_id": cloud_id}


@router.get("/issue")
async def jira_issue(request: Request, response: Response, issue_key: str) -> Dict[str, Any]:
    sid = _ensure_sid(request, response)
    session = get_session(sid) or {}

    client = _jira_client_from_session(session, request)

    try:
        issue = await client.get_issue(issue_key)
    except PermissionError:
        raise HTTPException(401, "Token expiré — reconnecte-toi via /login")
    except httpx.HTTPStatusError as e:
        # propager le status Jira (souvent 400) avec un petit snippet
        snippet = (e.response.text or "")[:300].replace("\n", " ")
        raise HTTPException(e.response.status_code, f"Jira error: {snippet}")
    except Exception:
        raise HTTPException(502, "Erreur lors de l'appel Jira (get_issue)")

    return _map_issue(issue)


@router.get("/search")
async def jira_search(
    request: Request,
    response: Response,
    jql: str,
    max_results: int = 20,
    next_page_token: str | None = None,
) -> Dict[str, Any]:
    if max_results < 1 or max_results > 100:
        raise HTTPException(400, "max_results doit être entre 1 et 100")

    sid = _ensure_sid(request, response)
    session = get_session(sid) or {}

    client = _jira_client_from_session(session, request)

    try:
        data = await client.search_jql(jql=jql, max_results=max_results, next_page_token=next_page_token)
    except PermissionError:
        raise HTTPException(401, "Token expiré — reconnecte-toi via /login")
    except httpx.HTTPStatusError as e:
        # propager le status Jira (souvent 400) avec un petit snippet
        snippet = (e.response.text or "")[:300].replace("\n", " ")
        raise HTTPException(e.response.status_code, f"Jira error: {snippet}")
    except Exception:
        raise HTTPException(502, "Erreur lors de l'appel Jira (search_jql)")

    return _map_search_result(data)


@router.get("/instances")
async def jira_instances(request: Request, response: Response) -> Dict[str, Any]:
    sid = _ensure_sid(request, response)
    session = get_session(sid) or {}

    sites = session.get("jira_sites") or []
    safe_sites = []
    for s in sites:
        if isinstance(s, dict):
            safe_sites.append({"id": s.get("id"), "name": s.get("name"), "url": s.get("url")})

    return {
        "cloud_ids": session.get("cloud_ids") or [],
        "active_cloud_id": session.get("active_cloud_id"),
        "jira_sites": safe_sites,
    }
