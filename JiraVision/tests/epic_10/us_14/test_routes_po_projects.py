import httpx

from fastapi.testclient import TestClient

from app.main import create_app

app = create_app()
client = TestClient(app)


def _mock_session():
    return {"jira_account_id": "acct"}


def test_list_projects_splits_active_inactive(monkeypatch):
    monkeypatch.setattr("app.routes.po_projects.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.po_projects.get_session", lambda sid: _mock_session())

    monkeypatch.setattr(
        "app.routes.po_projects.po_project_store.list_projects_for_user",
        lambda jid: [
            {"project_key": "A", "is_active": False},
            {"project_key": "B", "is_active": True},
            {"project_key": "C"},
        ],
    )
    monkeypatch.setattr(
        "app.routes.po_projects.po_project_store.get_user",
        lambda jid: {"last_synced_at": 123},
    )

    r = client.get("/po/projects")
    assert r.status_code == 200
    data = r.json()
    assert {p["project_key"] for p in data["projects"]} == {"B", "C"}
    assert {p["project_key"] for p in data["inactive_projects"]} == {"A"}
    assert data["last_synced_at"] == 123


def test_list_projects_requires_login(monkeypatch):
    monkeypatch.setattr("app.routes.po_projects.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.po_projects.get_session", lambda sid: {})

    r = client.get("/po/projects")
    assert r.status_code == 401


def test_add_project_invalid_source(monkeypatch):
    monkeypatch.setattr("app.routes.po_projects.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.po_projects.get_session", lambda sid: _mock_session())

    def _boom(*_a, **_k):
        raise ValueError("Invalid source: bad")

    monkeypatch.setattr("app.routes.po_projects.po_project_store.upsert_project_for_user", _boom)

    r = client.post(
        "/po/projects",
        json={"project_key": "P", "project_name": "Proj", "source": "bad"},
    )
    assert r.status_code == 400


def test_add_project_ok(monkeypatch):
    monkeypatch.setattr("app.routes.po_projects.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.po_projects.get_session", lambda sid: _mock_session())

    monkeypatch.setattr(
        "app.routes.po_projects.po_project_store.upsert_project_for_user",
        lambda *a, **k: {"project_key": "P", "source": "manual"},
    )

    r = client.post(
        "/po/projects",
        json={"project_key": "P", "project_name": "Proj"},
    )
    assert r.status_code == 200
    assert r.json()["project"]["project_key"] == "P"


def test_delete_project_mask_errors(monkeypatch):
    monkeypatch.setattr("app.routes.po_projects.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.po_projects.get_session", lambda sid: _mock_session())

    def _missing(*_a, **_k):
        raise KeyError("Project not found")

    monkeypatch.setattr("app.routes.po_projects.po_project_store.set_project_mask", _missing)

    r = client.request(
        "DELETE",
        "/po/projects/PRJ",
        json={"mask_type": "temporaire"},
    )
    assert r.status_code == 404


def test_delete_project_mask_invalid(monkeypatch):
    monkeypatch.setattr("app.routes.po_projects.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.po_projects.get_session", lambda sid: _mock_session())

    def _invalid(*_a, **_k):
        raise ValueError("Invalid mask_type")

    monkeypatch.setattr("app.routes.po_projects.po_project_store.set_project_mask", _invalid)

    r = client.request(
        "DELETE",
        "/po/projects/PRJ",
        json={"mask_type": "bad"},
    )
    assert r.status_code == 400


def test_delete_project_mask_ok(monkeypatch):
    monkeypatch.setattr("app.routes.po_projects.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.po_projects.get_session", lambda sid: _mock_session())

    monkeypatch.setattr(
        "app.routes.po_projects.po_project_store.set_project_mask",
        lambda *a, **k: {"project_key": "PRJ", "mask_type": "temporaire"},
    )

    r = client.request(
        "DELETE",
        "/po/projects/PRJ",
        json={"mask_type": "temporaire"},
    )
    assert r.status_code == 200


def test_refresh_projects_success_and_errors(monkeypatch):
    monkeypatch.setattr("app.routes.po_projects.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.po_projects.get_session", lambda sid: _mock_session())

    async def _ok(*_a, **_k):
        return {"projects": [], "inactive_projects": []}

    monkeypatch.setattr("app.routes.po_projects.po_project_sync.sync_projects_for_user", _ok)

    r = client.post("/po/projects/refresh", json={"reset_definitif": True})
    assert r.status_code == 200

    async def _perm(*_a, **_k):
        raise PermissionError()

    monkeypatch.setattr("app.routes.po_projects.po_project_sync.sync_projects_for_user", _perm)
    r = client.post("/po/projects/refresh", json={"reset_definitif": True})
    assert r.status_code == 401

    async def _http_err(*_a, **_k):
        req = httpx.Request("GET", "http://x")
        resp = httpx.Response(400, request=req, content=b"bad")
        raise httpx.HTTPStatusError("err", request=req, response=resp)

    monkeypatch.setattr("app.routes.po_projects.po_project_sync.sync_projects_for_user", _http_err)
    r = client.post("/po/projects/refresh", json={"reset_definitif": True})
    assert r.status_code == 400

    async def _boom(*_a, **_k):
        raise RuntimeError("boom")

    monkeypatch.setattr("app.routes.po_projects.po_project_sync.sync_projects_for_user", _boom)
    r = client.post("/po/projects/refresh", json={"reset_definitif": True})
    assert r.status_code == 502
