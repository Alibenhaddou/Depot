from __future__ import annotations

from typing import Any, Dict, Optional, List

import httpx
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.auth.session_store import ensure_session
from app.core.redis import get_session
from app.core import po_project_store
from app.core import po_project_sync

router = APIRouter(prefix="/po/projects", tags=["po-projects"])


class ProjectAddRequest(BaseModel):
    project_key: str = Field(..., min_length=1)
    project_name: str = Field(..., min_length=1)
    cloud_id: Optional[str] = None
    source: str = "manual"
    # Permet d'ajouter un projet inactif depuis la liste dédiée
    is_active: Optional[bool] = True
    inactive_at: Optional[int] = None


class ProjectMaskRequest(BaseModel):
    mask_type: str
    cloud_id: Optional[str] = None


class RefreshRequest(BaseModel):
    # En refresh manuel, on peut réinitialiser les masquages définitifs
    reset_definitif: bool = True


def _ensure_session(request: Request, response: Response) -> Dict[str, Any]:
    sid = ensure_session(request, response)
    session = get_session(sid) or {}
    # Jira account id est injecté au login OAuth (US-12)
    if not session.get("jira_account_id"):
        raise HTTPException(401, "Connecte-toi d'abord via Login Atlassian")
    return session


def _split_active_inactive(projects: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
    active: List[Dict[str, Any]] = []
    inactive: List[Dict[str, Any]] = []
    for p in projects:
        if p.get("is_active") is False:
            inactive.append(p)
        else:
            active.append(p)
    return {"projects": active, "inactive_projects": inactive}


@router.get("")
async def list_projects(request: Request, response: Response) -> Dict[str, Any]:
    session = _ensure_session(request, response)
    jira_account_id = session["jira_account_id"]

    projects = po_project_store.list_projects_for_user(jira_account_id)
    split = _split_active_inactive(projects)
    user = po_project_store.get_user(jira_account_id) or {}

    return {
        **split,
        "last_synced_at": user.get("last_synced_at"),
    }


@router.post("")
async def add_project(
    request: Request,
    response: Response,
    payload: ProjectAddRequest,
) -> Dict[str, Any]:
    session = _ensure_session(request, response)
    jira_account_id = session["jira_account_id"]

    try:
        project = po_project_store.upsert_project_for_user(
            jira_account_id,
            project_key=payload.project_key,
            project_name=payload.project_name,
            source=payload.source,
            cloud_id=payload.cloud_id,
            is_active=payload.is_active,
            inactive_at=payload.inactive_at,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    return {"project": project}


@router.delete("/{project_key}")
async def delete_project(
    project_key: str,
    request: Request,
    response: Response,
    payload: ProjectMaskRequest,
) -> Dict[str, Any]:
    session = _ensure_session(request, response)
    jira_account_id = session["jira_account_id"]

    try:
        project = po_project_store.set_project_mask(
            jira_account_id,
            project_key=project_key,
            cloud_id=payload.cloud_id,
            mask_type=payload.mask_type,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc

    return {"project": project}


@router.post("/refresh")
async def refresh_projects(
    request: Request,
    response: Response,
    payload: RefreshRequest,
) -> Dict[str, Any]:
    session = _ensure_session(request, response)
    jira_account_id = session["jira_account_id"]

    try:
        data = await po_project_sync.sync_projects_for_user(
            jira_account_id,
            session,
            reset_definitif=payload.reset_definitif,
        )
    except PermissionError:
        raise HTTPException(401, "Token expiré — reconnecte-toi via /login")
    except httpx.HTTPStatusError as exc:
        snippet = (exc.response.text or "")[:300].replace("\n", " ")
        raise HTTPException(exc.response.status_code, f"Jira error: {snippet}")
    except Exception:
        raise HTTPException(502, "Erreur lors du refresh Jira")

    return data
