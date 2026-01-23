import asyncio

import pytest

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import create_app
from app.routes import auth as auth_mod

app = create_app()
client = TestClient(app)


def test_get_accessible_resources_http_error(monkeypatch):
    async def fake_get(self, url, headers=None):
        class R:
            status_code = 500

            def json(self):
                return {}

        return R()

    class FakeAsyncClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def get(self, url, headers=None):
            return await fake_get(self, url, headers=headers)

    monkeypatch.setattr("app.routes.auth.httpx.AsyncClient", FakeAsyncClient)

    with pytest.raises(HTTPException) as e:
        asyncio.run(auth_mod._get_accessible_resources("tok"))
    assert e.value.status_code == 502


def test_pick_jira_resources_filters():
    resources = [
        {"id": "1", "url": "u", "scopes": ["read:jira-work"]},
        {"id": "2", "url": "u", "scopes": ["other:scope"]},
        {"id": None, "url": "u", "scopes": ["read:jira-work"]},
        {"id": "3", "url": None, "scopes": ["jira:write"]},
    ]

    out = auth_mod._pick_jira_resources(resources)
    assert len(out) == 1
    assert out[0]["id"] == "1"


def test_oauth_callback_token_errors(monkeypatch):
    # ensure session state exists
    monkeypatch.setattr("app.routes.auth.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.auth.get_session", lambda sid: {"state": "s123"})

    # token endpoint returns 500
    class FakeClientErr:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *a, **k):
            class R:
                status_code = 500

                def json(self):
                    return {}

            return R()

    monkeypatch.setattr("app.routes.auth.httpx.AsyncClient", FakeClientErr)

    r = client.get("/oauth/callback?code=code&state=s123", follow_redirects=False)
    assert r.status_code == 502


def test_oauth_callback_missing_access_token(monkeypatch):
    monkeypatch.setattr("app.routes.auth.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.auth.get_session", lambda sid: {"state": "s123"})

    class FakeClientOK:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *a, **k):
            class R:
                status_code = 200

                def json(self):
                    return {}

            return R()

    monkeypatch.setattr("app.routes.auth.httpx.AsyncClient", FakeClientOK)

    r = client.get("/oauth/callback?code=code&state=s123", follow_redirects=False)
    assert r.status_code == 400


def test_oauth_callback_success(monkeypatch):
    monkeypatch.setattr("app.routes.auth.ensure_session", lambda req, resp: "sid")
    captured = {}

    def fake_set_session(sid, sess):
        captured["sess"] = sess

    monkeypatch.setattr("app.routes.auth.set_session", fake_set_session)
    monkeypatch.setattr("app.routes.auth.get_session", lambda sid: {"state": "s123"})

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *a, **k):
            class R:
                status_code = 200

                def json(self):
                    return {"access_token": "atok"}

            return R()

    monkeypatch.setattr("app.routes.auth.httpx.AsyncClient", FakeClient)

    # stub accessible resources
    async def fake_accessible(token):
        return [
            {"id": "c1", "url": "https://x", "scopes": ["read:jira-work"], "name": "C1"}
        ]

    monkeypatch.setattr("app.routes.auth._get_accessible_resources", fake_accessible)

    class FakeJiraClient:
        def __init__(self, *a, **k):
            pass

        async def get_myself(self):
            return {"accountId": "u1", "displayName": "User One"}

        async def aclose(self):
            return None

    monkeypatch.setattr("app.routes.auth.JiraClient", FakeJiraClient)
    monkeypatch.setattr("app.routes.auth.upsert_user_from_jira", lambda *a, **k: {"user_id": "u1"})

    r = client.get("/oauth/callback?code=code&state=s123", follow_redirects=False)
    assert r.status_code in (307, 302)
    assert captured["sess"]["tokens_by_cloud"]["c1"]["access_token"] == "atok"
    assert captured["sess"]["active_cloud_id"] == "c1"
