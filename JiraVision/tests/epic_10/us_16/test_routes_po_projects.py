from __future__ import annotations

from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.core import po_project_store as store
from app.routes import po_projects as po_projects_routes


def _force_local_store(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise RuntimeError("redis down")

    monkeypatch.setattr(store.redis_client, "get", _boom)
    monkeypatch.setattr(store.redis_client, "set", _boom)
    store._local_store.clear()


def _mock_session(monkeypatch, session: Dict[str, Any]):
    monkeypatch.setattr(po_projects_routes, "ensure_session", lambda _req, _res: "sid")
    monkeypatch.setattr(po_projects_routes, "get_session", lambda _sid: session)


@pytest.fixture(autouse=True)
def reset_store():
    store._local_store.clear()  # type: ignore[attr-defined]
    yield
    store._local_store.clear()  # type: ignore[attr-defined]


def test_list_projects_splits_active_inactive(monkeypatch):
    _force_local_store(monkeypatch)
    _mock_session(
        monkeypatch,
        {
            "access_token": "tok",
            "jira_account_id": "acct",
        },
    )

    store.upsert_project_for_user(
        "acct",
        project_key="A",
        project_name="Alpha",
        source="jira",
        is_active=True,
    )
    store.upsert_project_for_user(
        "acct",
        project_key="B",
        project_name="Beta",
        source="jira",
        is_active=False,
    )

    client = TestClient(create_app())
    resp = client.get("/po/projects")
    assert resp.status_code == 200
    data = resp.json()
    assert [p["project_key"] for p in data["projects"]] == ["A"]
    assert [p["project_key"] for p in data["inactive_projects"]] == ["B"]


def test_list_projects_requires_login(monkeypatch):
    _mock_session(monkeypatch, {})
    client = TestClient(create_app())
    resp = client.get("/po/projects")
    assert resp.status_code == 401


def test_add_project_ok(monkeypatch):
    _force_local_store(monkeypatch)
    _mock_session(
        monkeypatch,
        {
            "access_token": "tok",
            "jira_account_id": "acct",
        },
    )

    client = TestClient(create_app())
    resp = client.post(
        "/po/projects",
        json={
            "project_key": "PRJ",
            "project_name": "Projet",
            "source": "manual",
            "is_active": True,
        },
    )
    assert resp.status_code == 200
    payload = resp.json()["project"]
    assert payload["project_key"] == "PRJ"
    assert payload["source"] == "manual"


def test_add_project_invalid_source(monkeypatch):
    _force_local_store(monkeypatch)
    _mock_session(
        monkeypatch,
        {
            "access_token": "tok",
            "jira_account_id": "acct",
        },
    )

    client = TestClient(create_app())
    resp = client.post(
        "/po/projects",
        json={
            "project_key": "PRJ",
            "project_name": "Projet",
            "source": "invalid",
        },
    )
    assert resp.status_code == 400


def test_delete_project_mask_ok(monkeypatch):
    _force_local_store(monkeypatch)
    _mock_session(
        monkeypatch,
        {
            "access_token": "tok",
            "jira_account_id": "acct",
        },
    )

    store.upsert_project_for_user(
        "acct",
        project_key="PRJ",
        project_name="Projet",
        source="jira",
        cloud_id="c1",
    )

    client = TestClient(create_app())
    resp = client.request(
        "DELETE",
        "/po/projects/PRJ",
        json={"mask_type": "temporaire", "cloud_id": "c1"},
    )
    assert resp.status_code == 200
    payload = resp.json()["project"]
    assert payload["mask_type"] == "temporaire"


def test_delete_project_mask_missing(monkeypatch):
    _force_local_store(monkeypatch)
    _mock_session(
        monkeypatch,
        {
            "access_token": "tok",
            "jira_account_id": "acct",
        },
    )

    client = TestClient(create_app())
    resp = client.request(
        "DELETE",
        "/po/projects/PRJ",
        json={"mask_type": "temporaire"},
    )
    assert resp.status_code == 404


def test_refresh_projects_calls_sync_and_resets_definitif(monkeypatch):
    _force_local_store(monkeypatch)
    _mock_session(
        monkeypatch,
        {
            "access_token": "tok",
            "jira_account_id": "acct",
        },
    )

    store.upsert_project_for_user(
        "acct",
        project_key="PRJ",
        project_name="Projet",
        source="jira",
        mask_type="definitif",
    )

    async def _fake_sync(_acct, _session):
        return {"projects": [], "inactive_projects": []}

    monkeypatch.setattr(po_projects_routes.po_project_sync, "sync_projects_for_user", _fake_sync)

    client = TestClient(create_app())
    resp = client.post("/po/projects/refresh", json={"reset_definitif": True})
    assert resp.status_code == 200

    proj = store.get_project_for_user("acct", project_key="PRJ", cloud_id=None)
    assert proj["mask_type"] == "none"
