import httpx
import types

import pytest

from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import create_app

app = create_app()
client = TestClient(app)


def test_require_logged_in_raises():
    from app.routes.jira import _require_logged_in

    with pytest.raises(HTTPException) as ei:
        _require_logged_in({})
    assert ei.value.status_code == 401


def test_jira_select_invalid_cloud(monkeypatch):
    monkeypatch.setattr("app.routes.jira._ensure_sid", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.jira.get_session", lambda sid: {"cloud_ids": ["a"]})

    r = client.post("/jira/select", params={"cloud_id": "b"})
    assert r.status_code == 400


def test_jira_issue_permission_error(monkeypatch):
    monkeypatch.setattr("app.routes.jira._ensure_sid", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.jira.get_session", lambda sid: {"tokens_by_cloud": {"c1": {"access_token": "t"}}, "cloud_ids": ["c1"], "active_cloud_id": "c1"})

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def get_issue(self, *a, **k):
            raise PermissionError()

    monkeypatch.setattr("app.routes.jira.JiraClient", FakeClient)

    r = client.get("/jira/issue", params={"issue_key": "P-1"})
    assert r.status_code == 401


def test_jira_issue_generic_exception(monkeypatch):
    monkeypatch.setattr("app.routes.jira._ensure_sid", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.jira.get_session", lambda sid: {"tokens_by_cloud": {"c1": {"access_token": "t"}}, "cloud_ids": ["c1"], "active_cloud_id": "c1"})

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def get_issue(self, *a, **k):
            raise Exception("boom")

    monkeypatch.setattr("app.routes.jira.JiraClient", FakeClient)

    r = client.get("/jira/issue", params={"issue_key": "P-1"})
    assert r.status_code == 502


def test_jira_search_httpstatus_propagates(monkeypatch):
    monkeypatch.setattr("app.routes.jira._ensure_sid", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.jira.get_session", lambda sid: {"tokens_by_cloud": {"c1": {"access_token": "t"}}, "cloud_ids": ["c1"], "active_cloud_id": "c1"})

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def search_jql(self, *a, **k):
            req = httpx.Request("POST", "http://x")
            resp = httpx.Response(400, request=req, content=b"bad")
            raise httpx.HTTPStatusError("err", request=req, response=resp)

    monkeypatch.setattr("app.routes.jira.JiraClient", FakeClient)

    r = client.get("/jira/search", params={"jql": "x"})
    assert r.status_code == 400


def test_jira_search_generic_exception(monkeypatch):
    monkeypatch.setattr("app.routes.jira._ensure_sid", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.jira.get_session", lambda sid: {"tokens_by_cloud": {"c1": {"access_token": "t"}}, "cloud_ids": ["c1"], "active_cloud_id": "c1"})

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def search_jql(self, *a, **k):
            raise Exception("boom")

    monkeypatch.setattr("app.routes.jira.JiraClient", FakeClient)

    r = client.get("/jira/search", params={"jql": "x"})
    assert r.status_code == 502
