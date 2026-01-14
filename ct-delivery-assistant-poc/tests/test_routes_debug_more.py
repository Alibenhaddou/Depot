import os
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import create_app
from app.routes import debug as dbg

app = create_app()
client = TestClient(app)


def test_enabled_flag_controls_routes(monkeypatch):
    # create app with debug disabled
    monkeypatch.setenv("ENABLE_DEBUG_ROUTES", "0")
    from app.main import create_app
    from fastapi.testclient import TestClient as _TC

    a1 = create_app()
    c1 = _TC(a1)
    r = c1.get("/debug/routes")
    assert r.status_code == 404

    # create app with debug enabled
    monkeypatch.setenv("ENABLE_DEBUG_ROUTES", "1")
    a2 = create_app()
    c2 = _TC(a2)
    r2 = c2.get("/debug/routes")
    assert r2.status_code == 200
    assert "jira_issue" in r2.json()


def test_debug_cookie_and_session(monkeypatch):
    # create app with debug enabled
    monkeypatch.setenv("ENABLE_DEBUG_ROUTES", "1")
    from app.main import create_app
    from fastapi.testclient import TestClient as _TC

    a = create_app()
    c = _TC(a)

    # no cookie -> cookie route should show sid_cookie_present False
    r = c.get("/debug/cookie")
    assert r.status_code == 200
    assert r.json()["sid_cookie_present"] is False

    # simulate a valid sid cookie and session in redis by patching get_sid/get_session
    monkeypatch.setattr("app.routes.debug.get_sid", lambda req: "s1")
    monkeypatch.setattr(
        "app.routes.debug.get_session",
        lambda sid: {
            "access_token": "t",
            "jira_sites": [{"id": "x", "name": "N", "url": "u"}],
        },
    )

    r2 = c.get("/debug/cookie", cookies={"sid": "v", "oauth_state": "o"})
    assert r2.json()["sid_cookie_present"] is True
    assert r2.json()["redis_session_present"] is True
    assert r2.json()["has_access_token"] is True

    # session route requires sid present and session; patch get_sid to None -> 401
    monkeypatch.setattr("app.routes.debug.get_sid", lambda req: None)
    r3 = c.get("/debug/session")
    assert r3.status_code == 401

    # patch get_sid and get_session to return partial session
    monkeypatch.setattr("app.routes.debug.get_sid", lambda req: "s1")
    monkeypatch.setattr(
        "app.routes.debug.get_session",
        lambda sid: {
            "tokens_by_cloud": {"c1": {}},
            "cloud_ids": ["c1"],
            "active_cloud_id": "c1",
            "jira_sites": [{"id": "x", "name": "N", "url": "u"}],
        },
    )

    r4 = c.get("/debug/session")
    assert r4.status_code == 200
    assert r4.json()["has_access_token"] is True
    assert r4.json()["jira_sites"][0]["id"] == "x"


def test_fingerprint_is_consistent():
    s = dbg._fingerprint("abc")
    assert isinstance(s, str) and len(s) == 12
