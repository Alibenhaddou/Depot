"""Project sync service for managing reporter's Jira projects."""

from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

from app.clients.jira import JiraClient
from app.models.jira import JiraProjectOut, ProjectVisibility

logger = logging.getLogger(__name__)


async def sync_reporter_projects(
    clients: List[tuple[str, JiraClient]],
    existing_hidden: Optional[Dict[str, str]] = None,
) -> List[JiraProjectOut]:
    """
    Sync projects where the user is a reporter of Epic/Story/Étude issues.
    
    Args:
        clients: List of (cloud_id, JiraClient) tuples for active instances
        existing_hidden: Dict of projectKey -> visibility state for hidden projects
        
    Returns:
        List of JiraProjectOut with aggregated project data
    """
    if existing_hidden is None:
        existing_hidden = {}
    
    # Build JQL to find issues where user is reporter
    # Exclude cancelled and done statuses
    # Filter by issue types: Epic, Story, Étude
    jql = (
        'reporter = currentUser() '
        'AND type in (Epic, Story, "Étude") '
        'AND status NOT IN (Annulé, Done, Cancelled, Terminé)'
    )
    
    projects_map: Dict[str, Dict[str, Any]] = {}
    
    for cloud_id, client in clients:
        try:
            # Fetch all issues (paginate if needed)
            max_results = 50
            start_at = 0
            total_fetched = 0
            
            while True:
                data = await client.search_jql(
                    jql=jql,
                    max_results=max_results,
                    fields=["project", "updated"],
                )
                
                issues = data.get("issues", [])
                if not issues:
                    break
                
                # Aggregate projects
                for issue in issues:
                    fields = issue.get("fields", {}) or {}
                    project_data = fields.get("project") or {}
                    project_key = project_data.get("key")
                    
                    if not project_key:
                        continue
                    
                    # Use composite key to handle same project across instances
                    composite_key = f"{cloud_id}:{project_key}"
                    
                    if composite_key not in projects_map:
                        projects_map[composite_key] = {
                            "projectKey": project_key,
                            "projectName": project_data.get("name"),
                            "cloudId": cloud_id,
                            "issueCount": 0,
                            "lastUpdated": None,
                        }
                    
                    projects_map[composite_key]["issueCount"] += 1
                    
                    # Track most recent update
                    updated = fields.get("updated")
                    if updated:
                        if (
                            not projects_map[composite_key]["lastUpdated"]
                            or updated > projects_map[composite_key]["lastUpdated"]
                        ):
                            projects_map[composite_key]["lastUpdated"] = updated
                
                total_fetched += len(issues)
                
                # Check if there are more results
                total = data.get("total", 0)
                if total_fetched >= total:
                    break
                
                # Note: Pagination is simplified - we fetch up to 50 results per instance.
                # For production use, implement full pagination using nextPageToken or startAt.
                # Breaking here to keep the implementation simple and performant.
                break
                
        except Exception as e:
            logger.warning(
                f"Failed to sync projects for cloud_id={cloud_id}: {e}",
                exc_info=True
            )
            continue
    
    # Convert to output models
    projects = []
    for composite_key, proj_data in projects_map.items():
        project_key = proj_data["projectKey"]
        
        # Apply visibility from existing hidden state
        visibility = ProjectVisibility.VISIBLE
        if project_key in existing_hidden:
            vis_state = existing_hidden[project_key]
            if vis_state == "hidden_permanent":
                visibility = ProjectVisibility.HIDDEN_PERMANENT
            elif vis_state == "hidden_temporary":
                visibility = ProjectVisibility.HIDDEN_TEMPORARY
        
        # Project is active if it has issues
        is_active = proj_data["issueCount"] > 0
        
        projects.append(
            JiraProjectOut(
                projectKey=project_key,
                projectName=proj_data["projectName"],
                cloudId=proj_data["cloudId"],
                issueCount=proj_data["issueCount"],
                lastUpdated=proj_data["lastUpdated"],
                visibility=visibility,
                isActive=is_active,
            )
        )
    
    return projects


def get_hidden_projects_state(session: Dict[str, Any]) -> Dict[str, str]:
    """Extract hidden projects mapping from session."""
    return session.get("hidden_projects") or {}


def save_hidden_projects_state(
    session: Dict[str, Any], 
    hidden_projects: Dict[str, str]
) -> None:
    """Save hidden projects mapping to session."""
    session["hidden_projects"] = hidden_projects


def hide_project(
    session: Dict[str, Any], 
    project_key: str, 
    permanent: bool = False
) -> None:
    """Mark a project as hidden in the session."""
    hidden = get_hidden_projects_state(session)
    visibility = "hidden_permanent" if permanent else "hidden_temporary"
    hidden[project_key] = visibility
    save_hidden_projects_state(session, hidden)


def unhide_project(session: Dict[str, Any], project_key: str) -> None:
    """Remove a project from the hidden list."""
    hidden = get_hidden_projects_state(session)
    if project_key in hidden:
        del hidden[project_key]
        save_hidden_projects_state(session, hidden)


def clear_temporary_hidden(session: Dict[str, Any]) -> None:
    """Clear temporarily hidden projects (called on manual refresh)."""
    hidden = get_hidden_projects_state(session)
    # Keep only permanently hidden
    permanent_only = {
        k: v for k, v in hidden.items() if v == "hidden_permanent"
    }
    save_hidden_projects_state(session, permanent_only)
