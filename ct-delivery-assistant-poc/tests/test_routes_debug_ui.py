import os
import types

from fastapi.testclient import TestClient
from fastapi.responses import Response

from app.main import create_app

app = create_app()
client = TestClient(app)


def test_debug_routes_disabled_by_default(monkeypatch):
    # ensure env var not set
    monkeypatch.delenv("ENABLE_DEBUG_ROUTES", raising=False)

    r = client.get("/debug/routes")
    assert r.status_code == 404


def test_debug_cookie_and_session(monkeypatch):
    monkeypatch.setenv("ENABLE_DEBUG_ROUTES", "1")

    # recreate app so router inclusion reflects the env var
    from app.main import create_app
    app_local = create_app()
    local_client = TestClient(app_local)

    # no sid cookie
    monkeypatch.setattr("app.routes.debug.get_sid", lambda req: None)
    r = local_client.get("/debug/cookie")
    assert r.status_code == 200
    assert r.json()["sid_cookie_present"] is False

    # with sid and session
    monkeypatch.setattr("app.routes.debug.get_sid", lambda req: "s1")
    session = {"access_token": "t", "tokens_by_cloud": {"c1": {}}, "jira_sites": [{"id": "c1", "name": "C1", "url": "https://x"}], "cloud_ids": ["c1"], "active_cloud_id": "c1", "site_url": "u"}
    monkeypatch.setattr("app.routes.debug.get_session", lambda sid: session)

    r2 = local_client.get("/debug/cookie")
    assert r2.status_code == 200
    j = r2.json()
    assert j["redis_session_present"] is True
    assert j["has_access_token"] is True

    # session endpoint
    r3 = local_client.get("/debug/session")
    assert r3.status_code == 200
    j2 = r3.json()
    assert j2["active_cloud_id"] == "c1"
    assert isinstance(j2["jira_sites"], list)


def test_ui_page_and_state(monkeypatch):
    # not logged in -> redirect to /auth
    monkeypatch.setattr("app.routes.ui.ensure_session", lambda req, resp: "sid-ui")
    monkeypatch.setattr("app.routes.ui.get_session", lambda sid: {})

    r = client.get("/ui", follow_redirects=False)
    assert r.status_code in (302, 307) or r.headers.get("location") == "/auth"

    # logged in -> return HTML
    monkeypatch.setattr("app.routes.ui.get_session", lambda sid: {"access_token": "t"})
    r2 = client.get("/ui")
    assert r2.status_code == 200
    assert "html" in r2.headers.get("content-type")

    # state endpoint
    r3 = client.get("/ui/state")
    assert r3.status_code == 200
    assert r3.json()["logged_in"] in (True, False)
