import asyncio
import types

import pytest

from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import create_app

app = create_app()
client = TestClient(app)


def test_debug_cookie_and_session(monkeypatch):
    monkeypatch.setenv("ENABLE_DEBUG_ROUTES", "1")
    from app.main import create_app

    # build a fresh app with debug routes enabled
    app = create_app()
    local_client = TestClient(app)

    # no sid cookie/session
    monkeypatch.setattr("app.routes.debug.get_sid", lambda req: None)
    monkeypatch.setattr("app.routes.debug.get_session", lambda sid: None)

    r = local_client.get("/debug/cookie")
    assert r.status_code == 200
    data = r.json()
    assert data["sid_cookie_present"] is False
    assert data["sid_fingerprint"] is None
    assert data["redis_session_present"] is False

    # with sid cookie and session containing tokens
    local_client.cookies.set("sid", "sval")
    local_client.cookies.set("oauth_state", "x")
    monkeypatch.setattr("app.routes.debug.get_sid", lambda req: "sid")
    monkeypatch.setattr(
        "app.routes.debug.get_session",
        lambda sid: {
            "access_token": "tok",
            "tokens_by_cloud": {"c": {}},
            "jira_sites": [{"id": "a", "name": "A", "url": "u"}, "bad"],
        },
    )

    r = local_client.get("/debug/cookie")
    assert r.status_code == 200
    data = r.json()
    assert data["sid_cookie_present"] is True
    assert data["sid_fingerprint"] is not None
    assert data["redis_session_present"] is True
    assert data["has_access_token"] is True
    assert data["oauth_state_cookie_present"] is True


def test_debug_session_errors_and_sanitizes_sites(monkeypatch):
    monkeypatch.setenv("ENABLE_DEBUG_ROUTES", "1")
    from app.main import create_app

    app = create_app()
    local_client = TestClient(app)

    # no sid -> 401
    monkeypatch.setattr("app.routes.debug.get_sid", lambda req: None)
    r = local_client.get("/debug/session")
    assert r.status_code == 401

    # sid but no session -> 401
    monkeypatch.setattr("app.routes.debug.get_sid", lambda req: "sid")
    monkeypatch.setattr("app.routes.debug.get_session", lambda sid: None)
    r = local_client.get("/debug/session")
    assert r.status_code == 401

    # sid and session -> sanitized jira_sites
    monkeypatch.setattr(
        "app.routes.debug.get_session",
        lambda sid: {
            "tokens_by_cloud": {},
            "jira_sites": [{"id": "x", "name": "X", "url": "u"}, "bad"],
        },
    )
    r = local_client.get("/debug/session")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data.get("jira_sites"), list)
    # ensure the non-dict entry was filtered out and dict kept
    assert data["jira_sites"][0]["id"] == "x"


class _FakeAsyncClient:
    def __init__(self, status=200, json_data=None):
        self._status = status
        self._json = json_data or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def get(self, url, headers=None):
        return types.SimpleNamespace(status_code=self._status, json=lambda: self._json)

    async def post(self, url, json=None, headers=None):
        return types.SimpleNamespace(status_code=self._status, json=lambda: self._json)


def test_get_accessible_resources_success_and_error(monkeypatch):
    # success
    monkeypatch.setattr(
        "app.routes.auth.httpx.AsyncClient",
        lambda *a, **k: _FakeAsyncClient(status=200, json_data=[{"id": "a"}]),
    )
    res = asyncio.run(
        __import__(
            "app.routes.auth", fromlist=["_get_accessible_resources"]
        )._get_accessible_resources("t")
    )
    assert isinstance(res, list)

    # error -> raises HTTPException (502)
    monkeypatch.setattr(
        "app.routes.auth.httpx.AsyncClient",
        lambda *a, **k: _FakeAsyncClient(status=500, json_data={}),
    )
    with pytest.raises(HTTPException):
        asyncio.run(
            __import__(
                "app.routes.auth", fromlist=["_get_accessible_resources"]
            )._get_accessible_resources("t")
        )


def test_oauth_callback_no_jira_resources(monkeypatch):
    # prepare session with matching state
    monkeypatch.setattr("app.routes.auth.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.auth.get_session", lambda sid: {"state": "s"})

    # token endpoint returns access_token
    monkeypatch.setattr(
        "app.routes.auth.httpx.AsyncClient",
        lambda *a, **k: _FakeAsyncClient(status=200, json_data={"access_token": "t"}),
    )

    # accessible resources returns none (no jira resources)
    import app.routes.auth as auth_mod

    async def fake_get_accessible(token):
        return []

    monkeypatch.setattr(auth_mod, "_get_accessible_resources", fake_get_accessible)

    # create a fresh app in case session handling is sensitive
    from app.main import create_app

    app = create_app()
    local_client = TestClient(app)

    r = local_client.get("/oauth/callback", params={"code": "c", "state": "s"})
    assert r.status_code == 400
    assert "Aucune ressource Jira" in r.text
