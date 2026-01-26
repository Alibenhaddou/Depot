from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from app.auth.session_store import ensure_session
from app.core.redis import get_session
from app.core import po_project_store, po_project_sync

router = APIRouter(prefix="/po/projects", tags=["po-projects"])


class ProjectPayload(BaseModel):
    project_key: str = Field(..., min_length=1)
    project_name: str = Field(..., min_length=1)
    source: str = "manual"
    cloud_id: Optional[str] = None
    is_active: Optional[bool] = True
    mask_type: str = "none"


class MaskPayload(BaseModel):
    mask_type: str
    cloud_id: Optional[str] = None


class RefreshPayload(BaseModel):
    reset_definitif: bool = False


def _get_session(request: Request, response: Response) -> Dict[str, Any]:
    sid = ensure_session(request, response)
    session = get_session(sid) or {}
    if not session.get("access_token") and not (session.get("tokens_by_cloud") or {}):
        raise HTTPException(401, "Connecte-toi d'abord via Login Atlassian")
    if not session.get("jira_account_id"):
        raise HTTPException(401, "Compte Jira introuvable")
    return session


def _split_projects(items: list[Dict[str, Any]]) -> Dict[str, list[Dict[str, Any]]]:
    active: list[Dict[str, Any]] = []
    inactive: list[Dict[str, Any]] = []
    for p in items:
        if p.get("is_active") is False:
            inactive.append(p)
        else:
            active.append(p)
    return {"active": active, "inactive": inactive}


@router.get("")
async def list_projects(request: Request, response: Response) -> Dict[str, Any]:
    session = _get_session(request, response)
    account_id = session.get("jira_account_id")

    # Correction bug #48 : filtrer les projets actifs selon la nouvelle règle métier
    items = po_project_store.list_projects_for_user(account_id)
    active_projects = []
    inactive_projects = []

    for p in items:
        # Récupérer le nombre de tickets Story/Etude non terminés/annulés assignés à l'utilisateur
        story_count = p.get("story_open_assigned_count", 0) or 0
        etude_count = p.get("etude_open_assigned_count", 0) or 0
        story_etude_count = story_count + etude_count

        if story_etude_count > 0:
            active_projects.append(p)
        else:
            inactive_projects.append(p)

    user = po_project_store.get_user(account_id) or {}

    return {
        "projects": active_projects,
        "inactive_projects": inactive_projects,
        "last_synced_at": user.get("last_synced_at"),
    }


@router.post("")
async def add_project(
    request: Request,
    response: Response,
    payload: ProjectPayload,
) -> Dict[str, Any]:
    session = _get_session(request, response)
    account_id = session.get("jira_account_id")

    try:
        project = po_project_store.upsert_project_for_user(
            account_id,
            project_key=payload.project_key.strip(),
            project_name=payload.project_name.strip(),
            source=payload.source,
            cloud_id=payload.cloud_id,
            mask_type=payload.mask_type,
            is_active=payload.is_active,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))

    return {"project": project}


@router.delete("/{project_key}")
async def mask_project(
    request: Request,
    response: Response,
    project_key: str,
    payload: MaskPayload,
) -> Dict[str, Any]:
    session = _get_session(request, response)
    account_id = session.get("jira_account_id")

    try:
        project = po_project_store.set_project_mask(
            account_id,
            project_key=project_key,
            cloud_id=payload.cloud_id,
            mask_type=payload.mask_type,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    except KeyError as exc:
        raise HTTPException(404, str(exc))

    return {"project": project}


@router.post("/refresh")
async def refresh_projects(
    request: Request,
    response: Response,
    payload: RefreshPayload,
) -> Dict[str, Any]:
    session = _get_session(request, response)
    account_id = session.get("jira_account_id")

    if payload.reset_definitif:
        for p in po_project_store.list_projects_for_user(account_id):
            if (p.get("mask_type") or "none") != "definitif":
                continue
            project_key = p.get("project_key") or ""
            if not project_key:
                continue
            try:
                po_project_store.set_project_mask(
                    account_id,
                    project_key=project_key,
                    cloud_id=p.get("cloud_id"),
                    mask_type="none",
                )
            except Exception:
                continue

    data = await po_project_sync.sync_projects_for_user(account_id, session)
    user = po_project_store.get_user(account_id) or {}

    return {
        **data,
        "last_synced_at": user.get("last_synced_at"),
    }
