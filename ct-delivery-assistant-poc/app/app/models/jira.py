from typing import Optional, List
from pydantic import BaseModel


class JiraIssueOut(BaseModel):  # type: ignore[misc]
    key: str
    summary: Optional[str] = None
    status: Optional[str] = None
    type: Optional[str] = None
    project: Optional[str] = None
    assignee: Optional[str] = None
    updated: Optional[str] = None


class JiraSearchResponse(BaseModel):  # type: ignore[misc]
    total: int
    startAt: int
    maxResults: int
    returned: int
    issues: List[JiraIssueOut]
