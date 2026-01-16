from __future__ import annotations

import httpx
from typing import Any, Dict
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request, Response

from app.auth.session_store import ensure_session
from app.core.redis import get_session, set_session
from app.clients.jira import JiraClient, select_cloud_id
from app.models.jira import JiraProjectsResponse
from app.services.project_sync import (
    sync_reporter_projects,
    get_hidden_projects_state,
    hide_project,
    unhide_project,
    clear_temporary_hidden,
)

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
    """Create a JiraClient using credentials stored in the user's session.

    Performs sanity checks: the user must be logged in (tokens present) and the
    selected `cloud_id` must exist and contain an access token. If not, a
    401 HTTPException is raised so the caller can return an appropriate error.
    """
    _require_logged_in(session)
    cloud_id = select_cloud_id(session, request)

    tbc = session.get("tokens_by_cloud") or {}
    entry = tbc.get(cloud_id)
    if not entry:
        raise HTTPException(
            401,
            "Instance Jira non connectée. Reconnecte-toi via /login.",
        )

    return JiraClient(access_token=entry["access_token"], cloud_id=cloud_id)


@router.post("/select")
async def jira_select(
    request: Request,
    response: Response,
    cloud_id: str,
) -> Dict[str, Any]:
    sid = _ensure_sid(request, response)
    session = get_session(sid) or {}

    ids = session.get("cloud_ids") or []
    if cloud_id not in ids:
        raise HTTPException(400, "cloud_id inconnu/non connecté")

    session["active_cloud_id"] = cloud_id
    set_session(sid, session)
    return {
        "ok": True,
        "active_cloud_id": cloud_id,
    }


@router.get("/issue")
async def jira_issue(
    request: Request,
    response: Response,
    issue_key: str,
) -> Dict[str, Any]:
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
        raise HTTPException(
            e.response.status_code,
            f"Jira error: {snippet}",
        )
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
        data = await client.search_jql(
            jql=jql,
            max_results=max_results,
            next_page_token=next_page_token,
        )
    except PermissionError:
        raise HTTPException(401, "Token expiré — reconnecte-toi via /login")
    except httpx.HTTPStatusError as e:
        # propager le status Jira (souvent 400) avec un petit snippet
        snippet = (e.response.text or "")[:300].replace("\n", " ")
        raise HTTPException(
            e.response.status_code,
            f"Jira error: {snippet}",
        )
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
            safe_sites.append(
                {"id": s.get("id"), "name": s.get("name"), "url": s.get("url")}
            )

    return {
        "cloud_ids": session.get("cloud_ids") or [],
        "active_cloud_id": session.get("active_cloud_id"),
        "jira_sites": safe_sites,
    }


@router.get("/projects/reporter", response_model=JiraProjectsResponse)
async def get_reporter_projects(
    request: Request, response: Response
) -> JiraProjectsResponse:
    """Get projects where the current user is a reporter.
    
    Returns projects from all active instances, excluding those with
    all issues in Done/Annulé status.
    """
    sid = _ensure_sid(request, response)
    session = get_session(sid) or {}
    _require_logged_in(session)
    
    # Get cached projects if available
    cached_projects = session.get("reporter_projects")
    last_sync = session.get("reporter_projects_sync_at")
    
    if cached_projects is not None:
        return JiraProjectsResponse(
            projects=cached_projects,
            total=len(cached_projects),
            lastSyncAt=last_sync,
        )
    
    # If not cached, trigger a sync
    return await sync_reporter_projects_endpoint(request, response)


@router.post("/projects/sync", response_model=JiraProjectsResponse)
async def sync_reporter_projects_endpoint(
    request: Request, response: Response
) -> JiraProjectsResponse:
    """Manually trigger sync of reporter's projects."""
    sid = _ensure_sid(request, response)
    session = get_session(sid) or {}
    _require_logged_in(session)
    
    # Clear temporarily hidden projects on manual refresh
    clear_temporary_hidden(session)
    
    # Get all active Jira instances
    tbc = session.get("tokens_by_cloud") or {}
    cloud_ids = session.get("cloud_ids") or []
    
    if not cloud_ids:
        # Return empty list if no instances connected
        session["reporter_projects"] = []
        session["reporter_projects_sync_at"] = datetime.now(timezone.utc).isoformat()
        set_session(sid, session)
        return JiraProjectsResponse(
            projects=[],
            total=0,
            lastSyncAt=session["reporter_projects_sync_at"],
        )
    
    # Create clients for all active instances
    clients = []
    for cloud_id in cloud_ids:
        entry = tbc.get(cloud_id)
        if entry and entry.get("access_token"):
            client = JiraClient(
                access_token=entry["access_token"],
                cloud_id=cloud_id,
            )
            clients.append((cloud_id, client))
    
    # Get existing hidden projects
    hidden = get_hidden_projects_state(session)
    
    try:
        # Sync projects
        projects = await sync_reporter_projects(clients, hidden)
        
        # Filter out hidden projects from the response
        visible_projects = [
            p for p in projects 
            if p.visibility.value == "visible"
        ]
        
        # Store in session
        # Convert to dict for JSON serialization
        session["reporter_projects"] = [p.model_dump() for p in visible_projects]
        session["reporter_projects_sync_at"] = datetime.now(timezone.utc).isoformat()
        set_session(sid, session)
        
        return JiraProjectsResponse(
            projects=visible_projects,
            total=len(visible_projects),
            lastSyncAt=session["reporter_projects_sync_at"],
        )
    except Exception as e:
        raise HTTPException(502, f"Erreur lors de la synchronisation: {str(e)}")
    finally:
        # Close all clients
        for _, client in clients:
            await client.aclose()


@router.post("/projects/{project_key}/hide")
async def hide_project_endpoint(
    request: Request,
    response: Response,
    project_key: str,
    permanent: bool = False,
) -> Dict[str, Any]:
    """Hide a project from the reporter's project list.
    
    Args:
        project_key: The project key to hide
        permanent: If True, hide permanently (survives manual refresh).
                  If False, hide temporarily (cleared on manual refresh).
    """
    sid = _ensure_sid(request, response)
    session = get_session(sid) or {}
    _require_logged_in(session)
    
    hide_project(session, project_key, permanent)
    
    # Update cached projects list
    cached_projects = session.get("reporter_projects") or []
    updated_projects = [
        p for p in cached_projects 
        if p.get("projectKey") != project_key
    ]
    session["reporter_projects"] = updated_projects
    
    set_session(sid, session)
    
    return {
        "ok": True,
        "projectKey": project_key,
        "hidden": True,
        "permanent": permanent,
    }


@router.post("/projects/{project_key}/unhide")
async def unhide_project_endpoint(
    request: Request, response: Response, project_key: str
) -> Dict[str, Any]:
    """Unhide a previously hidden project."""
    sid = _ensure_sid(request, response)
    session = get_session(sid) or {}
    _require_logged_in(session)
    
    unhide_project(session, project_key)
    set_session(sid, session)
    
    # Trigger a sync to get the project back
    await sync_reporter_projects_endpoint(request, response)
    
    return {
        "ok": True,
        "projectKey": project_key,
        "hidden": False,
    }
