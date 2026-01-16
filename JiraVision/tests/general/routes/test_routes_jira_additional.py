import httpx

from fastapi.testclient import TestClient

from app.main import create_app

app = create_app()
client = TestClient(app)


def test_jira_issue_http_status_error(monkeypatch):
    monkeypatch.setattr("app.routes.jira._ensure_sid", lambda req, resp: "sid")

    def fake_session():
        return {
            "tokens_by_cloud": {
                "c1": {"access_token": "t"},
            },
            "cloud_ids": ["c1"],
            "active_cloud_id": "c1",
        }

    monkeypatch.setattr(
        "app.routes.jira.get_session",
        lambda sid: fake_session(),
    )

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def get_issue(self, *a, **k):
            req = httpx.Request("GET", "http://x")
            resp = httpx.Response(400, request=req, content=b"bad")
            raise httpx.HTTPStatusError("err", request=req, response=resp)

    monkeypatch.setattr("app.routes.jira.JiraClient", FakeClient)

    r = client.get("/jira/issue", params={"issue_key": "P-1"})
    assert r.status_code == 400
    # Error should propagate Jira status and include snippet in detail
    assert r.json().get("detail", "").startswith("Jira error")


def test_jira_search_permission_error(monkeypatch):
    monkeypatch.setattr("app.routes.jira._ensure_sid", lambda req, resp: "sid")

    def fake_session():
        return {
            "tokens_by_cloud": {
                "c1": {"access_token": "t"},
            },
            "cloud_ids": ["c1"],
            "active_cloud_id": "c1",
        }

    monkeypatch.setattr(
        "app.routes.jira.get_session",
        lambda sid: fake_session(),
    )

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def search_jql(self, *a, **k):
            raise PermissionError()

    monkeypatch.setattr("app.routes.jira.JiraClient", FakeClient)

    r = client.get("/jira/search", params={"jql": "x"})
    assert r.status_code == 401


def test_jira_instances_filters_non_dict(monkeypatch):
    monkeypatch.setattr("app.routes.jira._ensure_sid", lambda req, resp: "sid")
    session = {
        "cloud_ids": ["a"],
        "active_cloud_id": "a",
        "jira_sites": [{"id": "a", "name": "A", "url": "u"}, "bad"],
    }
    monkeypatch.setattr("app.routes.jira.get_session", lambda sid: session)

    r = client.get("/jira/instances")
    assert r.status_code == 200
    data = r.json()
    assert data["jira_sites"][0]["id"] == "a"


def test_jira_instances_missing_and_bad_entries(monkeypatch):
    monkeypatch.setattr("app.routes.jira._ensure_sid", lambda req, resp: "sid")
    # session with no jira_sites and empty cloud_ids
    monkeypatch.setattr(
        "app.routes.jira.get_session",
        lambda sid: {"cloud_ids": [], "active_cloud_id": None},
    )

    r = client.get("/jira/instances")
    assert r.status_code == 200
    data = r.json()
    assert data["jira_sites"] == []
    assert data["cloud_ids"] == []
