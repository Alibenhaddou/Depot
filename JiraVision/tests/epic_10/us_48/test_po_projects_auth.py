import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

# Helpers pour simuler une session PO authentifiée (mock sid + patch get_session)

def make_auth_cookie(sid="test-session"):
    from itsdangerous import URLSafeSerializer
    s = URLSafeSerializer(settings.app_secret_key, salt="sid")
    signed_sid = s.dumps(sid)
    return {"sid": signed_sid}

def mock_get_session(monkeypatch, data=None, sid="test-session"):
    if data is None:
        data = {
            "access_token": "tok",
            "jira_account_id": "user-1",
            "tokens_by_cloud": {"cloud-1": {"access_token": "tok"}},
        }
    from app.core import redis as redis_mod
    redis_mod.set_session(sid, data)
    return data

def test_add_project_ok(monkeypatch):
    sid = "test-session"
    mock_get_session(monkeypatch, sid=sid)
    resp = client.post(
        "/po/projects",
        json={"project_key": "ABC", "project_name": "Projet Test"},
        cookies=make_auth_cookie(sid)
    )
    assert resp.status_code in (200, 201, 400)  # 400 si projet déjà existant
    if resp.status_code == 200:
        payload = resp.json()
        project = payload.get("project", payload)
        assert project["project_key"] == "ABC"

def test_list_projects_ok(monkeypatch):
    sid = "test-session"
    mock_get_session(
        monkeypatch,
        data={
            "jira_account_id": "user-1",
            "tokens_by_cloud": {"cloud-1": {"access_token": "tok"}},
        },
        sid=sid,
    )
    resp = client.get("/po/projects", cookies=make_auth_cookie(sid))
    assert resp.status_code == 200
    assert "projects" in resp.json()

def test_mask_project_notfound(monkeypatch):
    sid = "test-session"
    mock_get_session(monkeypatch, sid=sid)
    import json as pyjson
    payload = pyjson.dumps({"mask_type": "temporaire"})
    resp = client.request(
        "DELETE",
        "/po/projects/INEXISTANT",
        data=payload,
        headers={"Content-Type": "application/json"},
        cookies=make_auth_cookie(sid)
    )
    assert resp.status_code in (404, 400)

def test_refresh_projects_ok(monkeypatch):
    sid = "test-session"
    mock_get_session(monkeypatch, sid=sid)
    resp = client.post(
        "/po/projects/refresh",
        json={"reset_definitif": True},
        cookies=make_auth_cookie(sid)
    )
    assert resp.status_code == 200
    assert "last_synced_at" in resp.json()
