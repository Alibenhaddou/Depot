from __future__ import annotations

import logging
from typing import Any, Dict, List

import httpx

from app.clients.jira import JiraClient
from app.core import po_project_store

logger = logging.getLogger(__name__)
if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


def _active_projects_jql(account_id: str) -> str:
    return (
        f'reporter = "{account_id}" '
        'AND type in (Story, Etude) '
        'AND status NOT IN ("Done", "Annulé")'
    )


async def _fetch_reporter_projects(
    client: JiraClient,
    account_id: str,
) -> Dict[str, Dict[str, str]]:
    # Nouvelle JQL pour tickets actifs
    jql = _active_projects_jql(account_id)
    logger.debug(f"JQL projets actifs: {jql}")
    data = await client.search_jql(jql, max_results=100)
    issues = data.get("issues", []) if isinstance(data, dict) else []
    # Extraire les projets distincts à partir des tickets trouvés
    projects = {}
    for issue in issues:
        fields = issue.get("fields", {}) or {}
        proj = fields.get("project", {}) or {}
        key = proj.get("key")
        name = proj.get("name") or key
        if key:
            projects[key] = {"project_key": key, "project_name": name}
    logger.debug(f"Projets actifs trouvés: {list(projects.keys())}")
    return projects


async def sync_projects_for_user(
    jira_account_id: str,
    session: Dict[str, Any],
) -> Dict[str, Any]:
    tokens_by_cloud = session.get("tokens_by_cloud") or {}
    cloud_ids: List[str] = session.get("cloud_ids") or list(tokens_by_cloud.keys())

    if not jira_account_id or not cloud_ids:
        return {"projects": [], "inactive_projects": []}

    existing = {
        (p.get("cloud_id") or "default") + ":" + (p.get("project_key") or ""): p
        for p in po_project_store.list_projects_for_user(jira_account_id)
    }

    found_ids: set[str] = set()
    active_projects: List[Dict[str, Any]] = []
    inactive_projects: List[Dict[str, Any]] = []

    for cloud_id in cloud_ids:
        token_entry = tokens_by_cloud.get(cloud_id) or {}
        access_token = token_entry.get("access_token")
        if not access_token:
            continue

        client = JiraClient(access_token=access_token, cloud_id=cloud_id)
        try:
            projects = await _fetch_reporter_projects(client, jira_account_id)
            logger.debug(f"Projets actifs pour cloud_id={cloud_id}, user={jira_account_id}: {list(projects.keys())}")
            for project_key, project_info in projects.items():
                project_id = f"{cloud_id}:{project_key}"
                found_ids.add(project_id)

                prev = existing.get(project_id)
                prev_mask = (prev or {}).get("mask_type") or "none"
                mask_type = "none" if prev_mask == "temporaire" else prev_mask
                masked_at = (prev or {}).get("masked_at")

                project = po_project_store.upsert_project_for_user(
                    jira_account_id,
                    project_key=project_key,
                    project_name=project_info.get("project_name") or project_key,
                    source="jira",
                    cloud_id=cloud_id,
                    mask_type=mask_type,
                    masked_at=masked_at,
                    is_active=True,
                )
                active_projects.append(project)
        except PermissionError:
            logger.warning("Jira token expired for cloud_id=%s", cloud_id)
        except httpx.HTTPStatusError as exc:
            logger.warning("Jira search failed for cloud_id=%s: %s", cloud_id, exc)
        finally:
            await client.aclose()

    # Mark previously known jira projects not returned by reporter query as inactive
    for project_id, prev in existing.items():
        if project_id in found_ids:
            continue
        if prev.get("source") != "jira":
            continue
        cloud_id, project_key = project_id.split(":", 1)
        project = po_project_store.upsert_project_for_user(
            jira_account_id,
            project_key=project_key,
            project_name=prev.get("project_name") or project_key,
            source="jira",
            cloud_id=None if cloud_id == "default" else cloud_id,
            mask_type=prev.get("mask_type") or "none",
            masked_at=prev.get("masked_at"),
            is_active=False,
        )
        inactive_projects.append(project)

    po_project_store.set_last_synced_at(jira_account_id)

    return {
        "projects": active_projects,
        "inactive_projects": inactive_projects,
    }
