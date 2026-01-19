from __future__ import annotations

from typing import Any, Dict, List

import httpx

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
        # reporter query returns projects
        if "reporter" in jql:
            if self.cloud_id == "c1":
                return {
                    "issues": [
                        {"fields": {"project": {"key": "A", "name": "Alpha"}}},
                        {"fields": {"project": {"key": "B", "name": "Beta"}}},
                    ]
                }
            return {"issues": []}

        # epic status check
        if "type = Epic" in jql and "project = \"A\"" in jql:
            return {"issues": []}
        if "type = Epic" in jql and "project = \"B\"" in jql:
            return {"issues": [{"key": "B-1"}]}
        return {"issues": []}


@pytest.fixture(autouse=True)
def reset_store():
    po_project_store._local_store.clear()  # type: ignore[attr-defined]
    yield
    po_project_store._local_store.clear()  # type: ignore[attr-defined]


@pytest.mark.asyncio
async def test_sync_marks_active_and_inactive(monkeypatch):
    monkeypatch.setattr(po_project_sync, "JiraClient", FakeJiraClient)

    session = {
        "tokens_by_cloud": {
            "c1": {"access_token": "tok1"},
        },
        "cloud_ids": ["c1"],
    }

    data = await po_project_sync.sync_projects_for_user("u1", session)
    active = {p["project_key"]: p for p in data["projects"]}
    inactive = {p["project_key"]: p for p in data["inactive_projects"]}

    assert active["B"]["is_active"] is True
    assert inactive["A"]["is_active"] is False


@pytest.mark.asyncio
async def test_sync_status_and_mask(monkeypatch):
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

    assert inactive["A"]["is_active"] is False
    assert inactive["A"]["mask_type"] == "none"

    assert active["B"]["mask_type"] == "definitif"
    assert active["B"]["masked_at"] == 123


@pytest.mark.asyncio
async def test_sync_reset_definitif(monkeypatch):
    monkeypatch.setattr(po_project_sync, "JiraClient", FakeJiraClient)

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

    result = await po_project_sync.sync_projects_for_user(
        "u1",
        session,
        reset_definitif=True,
    )
    active = {p["project_key"]: p for p in result["projects"]}

    assert active["B"]["mask_type"] == "none"


@pytest.mark.asyncio
async def test_sync_returns_empty_when_missing_inputs():
    out = await po_project_sync.sync_projects_for_user("", {})
    assert out == {"projects": [], "inactive_projects": []}


@pytest.mark.asyncio
async def test_sync_skips_cloud_without_token(monkeypatch):
    monkeypatch.setattr(po_project_sync, "JiraClient", FakeJiraClient)

    session = {
        "tokens_by_cloud": {"c1": {}},
        "cloud_ids": ["c1"],
    }

    out = await po_project_sync.sync_projects_for_user("u1", session)
    assert out == {"projects": [], "inactive_projects": []}


@pytest.mark.asyncio
async def test_sync_epic_check_http_error(monkeypatch):
    class EpicErrorClient(FakeJiraClient):
        async def search_jql(self, jql: str, max_results: int = 20, next_page_token: str | None = None):
            if "type = Epic" in jql:
                req = httpx.Request("GET", "http://x")
                resp = httpx.Response(400, request=req, content=b"bad")
                raise httpx.HTTPStatusError("err", request=req, response=resp)
            return await super().search_jql(jql, max_results=max_results, next_page_token=next_page_token)

    monkeypatch.setattr(po_project_sync, "JiraClient", EpicErrorClient)

    session = {
        "tokens_by_cloud": {"c1": {"access_token": "tok1"}},
        "cloud_ids": ["c1"],
    }

    result = await po_project_sync.sync_projects_for_user("u1", session)
    active = {p["project_key"]: p for p in result["projects"]}
    # Epic check error => has_epic=True
    assert "A" in active


@pytest.mark.asyncio
async def test_sync_handles_permission_and_http_errors(monkeypatch):
    class ErrorClient(FakeJiraClient):
        async def search_jql(self, jql: str, max_results: int = 20, next_page_token: str | None = None):
            if "reporter" in jql:
                raise PermissionError()
            return await super().search_jql(jql, max_results=max_results, next_page_token=next_page_token)

    class HttpErrorClient(FakeJiraClient):
        async def search_jql(self, jql: str, max_results: int = 20, next_page_token: str | None = None):
            if "reporter" in jql:
                req = httpx.Request("GET", "http://x")
                resp = httpx.Response(400, request=req, content=b"bad")
                raise httpx.HTTPStatusError("err", request=req, response=resp)
            return await super().search_jql(jql, max_results=max_results, next_page_token=next_page_token)

    session = {
        "tokens_by_cloud": {"c1": {"access_token": "tok1"}},
        "cloud_ids": ["c1"],
    }

    monkeypatch.setattr(po_project_sync, "JiraClient", ErrorClient)
    out = await po_project_sync.sync_projects_for_user("u1", session)
    assert out == {"projects": [], "inactive_projects": []}

    monkeypatch.setattr(po_project_sync, "JiraClient", HttpErrorClient)
    out = await po_project_sync.sync_projects_for_user("u1", session)
    assert out == {"projects": [], "inactive_projects": []}


@pytest.mark.asyncio
async def test_sync_marks_previous_jira_projects_inactive(monkeypatch):
    monkeypatch.setattr(po_project_sync, "JiraClient", FakeJiraClient)

    po_project_store.upsert_project_for_user(
        "u1",
        project_key="Z",
        project_name="Zulu",
        source="jira",
        cloud_id="c1",
        mask_type="temporaire",
    )
    po_project_store.upsert_project_for_user(
        "u1",
        project_key="M",
        project_name="Manual",
        source="manual",
        cloud_id="c1",
    )

    class NoIssuesClient(FakeJiraClient):
        async def search_jql(self, jql: str, max_results: int = 20, next_page_token: str | None = None):
            if "reporter" in jql:
                return {"issues": []}
            return {"issues": []}

    monkeypatch.setattr(po_project_sync, "JiraClient", NoIssuesClient)

    session = {
        "tokens_by_cloud": {"c1": {"access_token": "tok1"}},
        "cloud_ids": ["c1"],
    }

    result = await po_project_sync.sync_projects_for_user("u1", session)
    inactive = {p["project_key"]: p for p in result["inactive_projects"]}
    assert inactive["Z"]["is_active"] is False
    # manual project should be ignored
    assert "M" not in inactive


@pytest.mark.asyncio
async def test_sync_inactive_resets_definitif_when_manual_refresh(monkeypatch):
    class NoIssuesClient(FakeJiraClient):
        async def search_jql(self, jql: str, max_results: int = 20, next_page_token: str | None = None):
            return {"issues": []}

    monkeypatch.setattr(po_project_sync, "JiraClient", NoIssuesClient)

    po_project_store.upsert_project_for_user(
        "u1",
        project_key="D",
        project_name="Delta",
        source="jira",
        cloud_id="c1",
        mask_type="definitif",
        masked_at=123,
    )
    po_project_store.upsert_project_for_user(
        "u1",
        project_key="N",
        project_name="None",
        source="jira",
        cloud_id="c1",
        mask_type="none",
    )

    session = {
        "tokens_by_cloud": {"c1": {"access_token": "tok1"}},
        "cloud_ids": ["c1"],
    }

    result = await po_project_sync.sync_projects_for_user(
        "u1",
        session,
        reset_definitif=True,
    )
    inactive = {p["project_key"]: p for p in result["inactive_projects"]}
    assert inactive["D"]["mask_type"] == "none"
    assert inactive["N"]["mask_type"] == "none"
