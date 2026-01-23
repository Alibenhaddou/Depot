from __future__ import annotations
from typing import Any, Dict, List
import pytest
from app.core import po_project_store
from app.core import po_project_sync

class FakeJiraClient:
    def __init__(self, access_token: str, cloud_id: str, timeout: int = 30):
        self.cloud_id = cloud_id
        self.calls: List[str] = []

    async def aclose(self) -> None:
        return None

    async def search_jql(self, jql: str, max_results: int = 20, next_page_token: str | None = None):
        self.calls.append(jql)
        # New logic: reporter query with Story/Etude types returns projects directly
        if "reporter" in jql and "type in (Story, Etude)" in jql:
            if self.cloud_id == "c1":
                # Only project B has active Story/Etude tickets (not Done/Annulé)
                return {
                    "issues": [
                        {"fields": {"project": {"key": "B", "name": "Beta"}}},
                    ]
                }
            return {"issues": []}
        return {"issues": []}


@pytest.fixture(autouse=True)
def reset_store():
    po_project_store._local_store.clear()  # type: ignore[attr-defined]
    yield
    po_project_store._local_store.clear()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_sync_marks_active_and_inactive(monkeypatch):
    """Test that projects with active Story/Etude tickets are marked active, others inactive."""
    monkeypatch.setattr(po_project_sync, "JiraClient", FakeJiraClient)

    # Pre-seed project A to test inactive marking
    po_project_store.upsert_project_for_user(
        "u1",
        project_key="A",
        project_name="Alpha",
        source="jira",
        cloud_id="c1",
    )

    session = {
        "tokens_by_cloud": {
            "c1": {"access_token": "tok1"},
        },
        "cloud_ids": ["c1"],
    }

    data = await po_project_sync.sync_projects_for_user("u1", session)
    active = {p["project_key"]: p for p in data["projects"]}
    inactive = {p["project_key"]: p for p in data["inactive_projects"]}

    # Project B has active Story/Etude tickets, should be active
    assert "B" in active
    assert active["B"]["is_active"] is True
    
    # Project A doesn't have active Story/Etude tickets, should be inactive
    assert "A" in inactive
    assert inactive["A"]["is_active"] is False


@pytest.mark.asyncio
async def test_sync_status_and_mask(monkeypatch):
    """Test that mask types are preserved during sync."""
    monkeypatch.setattr(po_project_sync, "JiraClient", FakeJiraClient)

    # pre-seed masked projects
    po_project_store.upsert_project_for_user(
        "u1",
        project_key="A",
        project_name="Alpha",
        source="jira",
        cloud_id="c1",
        mask_type="temporaire",
    )
    po_project_store.upsert_project_for_user(
        "u1",
        project_key="B",
        project_name="Beta",
        source="jira",
        cloud_id="c1",
        mask_type="definitif",
        masked_at=123,
    )

    session = {
        "tokens_by_cloud": {"c1": {"access_token": "tok1"}},
        "cloud_ids": ["c1"],
    }

    result = await po_project_sync.sync_projects_for_user("u1", session)
    active = {p["project_key"]: p for p in result["projects"]}
    inactive = {p["project_key"]: p for p in result["inactive_projects"]}

    # Project A: no active Story/Etude tickets, becomes inactive, temporaire mask preserved
    assert "A" in inactive
    assert inactive["A"]["is_active"] is False
    assert inactive["A"]["mask_type"] == "temporaire"

    # Project B: has active Story/Etude tickets, stays active, definitif mask preserved
    assert "B" in active
    assert active["B"]["mask_type"] == "definitif"
    assert active["B"]["masked_at"] == 123
