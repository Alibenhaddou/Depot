from __future__ import annotations

import logging
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from app.auth.session_store import ensure_session
from app.core.redis import get_session
from app.core import po_project_store, po_project_sync

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/po", tags=["po"])


class ProjectsResponse(BaseModel):
    projects: List[Dict[str, Any]]
    inactive_projects: List[Dict[str, Any]]
    last_synced_at: int | None


class RefreshRequest(BaseModel):
    reset_definitif: bool = False


class AddProjectRequest(BaseModel):
    project_key: str
    project_name: str
    cloud_id: str | None = None


class MaskProjectRequest(BaseModel):
    mask_type: str


def _get_jira_account_id(request: Request, response: Response) -> str:
    """Get the current user's Jira account ID from session."""
    sid = ensure_session(request, response)
    session = get_session(sid) or {}

    if not (session.get("access_token") or (session.get("tokens_by_cloud") or {})):
        raise HTTPException(401, "Non authentifié")
    
    jira_account_id = session.get("jira_account_id")
    if not jira_account_id:
        raise HTTPException(400, "jira_account_id manquant")
    
    return jira_account_id


def _filter_and_format_projects(
    projects: List[Dict[str, Any]],
    inactive: List[Dict[str, Any]]
) -> Dict[str, List[Dict[str, Any]]]:
    """Filter out masked projects and return active/inactive lists."""
    active_list = [p for p in projects if p.get("mask_type") == "none"]
    inactive_list = [p for p in inactive if p.get("mask_type") == "none"]
    
    return {
        "projects": active_list,
        "inactive_projects": inactive_list
    }


@router.get("/projects", response_model=ProjectsResponse)
async def get_projects(request: Request, response: Response) -> ProjectsResponse:
    """Get all projects for the current user."""
    jira_account_id = _get_jira_account_id(request, response)
    
    user = po_project_store.get_user(jira_account_id)
    last_synced_at = user.get("last_synced_at") if user else None
    
    all_projects = po_project_store.list_projects_for_user(jira_account_id)
    
    projects = [p for p in all_projects if p.get("is_active", True)]
    inactive = [p for p in all_projects if not p.get("is_active", True)]
    
    filtered = _filter_and_format_projects(projects, inactive)
    
    return ProjectsResponse(
        projects=filtered["projects"],
        inactive_projects=filtered["inactive_projects"],
        last_synced_at=last_synced_at
    )


@router.post("/projects/refresh", response_model=ProjectsResponse)
async def refresh_projects(
    req: RefreshRequest,
    request: Request,
    response: Response
) -> ProjectsResponse:
    """Refresh projects from Jira for the current user."""
    jira_account_id = _get_jira_account_id(request, response)
    sid = ensure_session(request, response)
    session = get_session(sid) or {}
    
    if req.reset_definitif:
        # Reset all definitif masks to none before sync
        all_projects = po_project_store.list_projects_for_user(jira_account_id)
        for proj in all_projects:
            if proj.get("mask_type") == "definitif":
                po_project_store.set_project_mask(
                    jira_account_id,
                    project_key=proj["project_key"],
                    cloud_id=proj.get("cloud_id"),
                    mask_type="none",
                )
    
    try:
        result = await po_project_sync.sync_projects_for_user(jira_account_id, session)
    except Exception as exc:
        logger.error("Erreur sync projets: %s", exc)
        raise HTTPException(502, "Erreur lors du rafraîchissement")
    
    filtered = _filter_and_format_projects(
        result.get("projects", []),
        result.get("inactive_projects", [])
    )
    
    user = po_project_store.get_user(jira_account_id)
    last_synced_at = user.get("last_synced_at") if user else None
    
    return ProjectsResponse(
        projects=filtered["projects"],
        inactive_projects=filtered["inactive_projects"],
        last_synced_at=last_synced_at
    )


@router.post("/projects", response_model=Dict[str, Any])
async def add_project(
    req: AddProjectRequest,
    request: Request,
    response: Response
) -> Dict[str, Any]:
    """Add a project manually."""
    jira_account_id = _get_jira_account_id(request, response)
    
    project = po_project_store.upsert_project_for_user(
        jira_account_id,
        project_key=req.project_key,
        project_name=req.project_name,
        source="manual",
        cloud_id=req.cloud_id,
        mask_type="none",
        is_active=True
    )
    
    return project


@router.delete("/projects/{project_key}", response_model=Dict[str, Any])
async def mask_project(
    project_key: str,
    req: MaskProjectRequest,
    request: Request,
    response: Response
) -> Dict[str, Any]:
    """Mask a project (temporaire or definitif)."""
    jira_account_id = _get_jira_account_id(request, response)
    
    if req.mask_type not in ("temporaire", "definitif"):
        raise HTTPException(400, "mask_type invalide")
    
    # Find the project to get its cloud_id
    all_projects = po_project_store.list_projects_for_user(jira_account_id)
    target_project = None
    for proj in all_projects:
        if proj.get("project_key") == project_key:
            target_project = proj
            break
    
    if not target_project:
        raise HTTPException(404, "Projet introuvable")
    
    project = po_project_store.set_project_mask(
        jira_account_id,
        project_key=project_key,
        cloud_id=target_project.get("cloud_id"),
        mask_type=req.mask_type
    )
    
    return project
