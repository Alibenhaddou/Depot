from typing import Optional, List
from pydantic import BaseModel
from enum import Enum


class JiraIssueOut(BaseModel):
    key: str
    summary: Optional[str] = None
    status: Optional[str] = None
    type: Optional[str] = None
    project: Optional[str] = None
    assignee: Optional[str] = None
    updated: Optional[str] = None


class JiraSearchResponse(BaseModel):
    total: int
    startAt: int
    maxResults: int
    returned: int
    issues: List[JiraIssueOut]


class ProjectVisibility(str, Enum):
    """Project visibility states."""
    VISIBLE = "visible"
    HIDDEN_TEMPORARY = "hidden_temporary"
    HIDDEN_PERMANENT = "hidden_permanent"


class JiraProjectOut(BaseModel):
    """Represents a Jira project where the user is a reporter."""
    projectKey: str
    projectName: Optional[str] = None
    cloudId: str
    issueCount: int = 0
    lastUpdated: Optional[str] = None
    visibility: ProjectVisibility = ProjectVisibility.VISIBLE
    isActive: bool = True


class JiraProjectsResponse(BaseModel):
    """Response for reporter's projects list."""
    projects: List[JiraProjectOut]
    total: int
    lastSyncAt: Optional[str] = None
