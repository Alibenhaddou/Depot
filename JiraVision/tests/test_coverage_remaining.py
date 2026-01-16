import json
import types
import asyncio

import pytest

from app.clients.llm import LLMClient
from app.core.config import Settings
from app.core import redis as core_redis
from app.main import _env_flag
from fastapi import HTTPException


def test_llm_openai_chat_text_returns_content(monkeypatch):
    from app.core import config as cfg

    monkeypatch.setattr(cfg.settings, "llm_provider", "openai")
    monkeypatch.setattr(cfg.settings, "openai_api_key", "k")
    monkeypatch.setattr(cfg.settings, "llm_timeout", 1)

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def post(self, url, json=None, headers=None):
            return types.SimpleNamespace(
                status_code=200,
                json=lambda: {"choices": [{"message": {"content": "hello"}}]},
                raise_for_status=lambda: None,
            )

    monkeypatch.setattr("app.clients.llm.httpx.AsyncClient", FakeClient)

    c = LLMClient()
    out = asyncio.run(c.chat_text(system="s", user="u"))
    assert out == "hello"


def test_settings_validators_raise_on_invalid():
    # invalid samesite
    with pytest.raises(Exception) as e1:
        Settings(
            atlassian_client_id="a",
            atlassian_client_secret="b",
            atlassian_redirect_uri="u",
            atlassian_scopes="s",
            app_secret_key="k",
            cookie_samesite="bad",
        )
    assert "cookie_samesite" in str(e1.value)

    # samesite=none requires cookie_secure True -> call validator directly
    import types as _types

    with pytest.raises(ValueError):
        Settings._validate_cookie_secure(
            False, info=_types.SimpleNamespace(data={"cookie_samesite": "none"})
        )


def test_get_session_handles_invalid_json_and_refresh_ttl(monkeypatch):
    core_redis._redis_available = True
    core_redis._redis_warned = False
    # invalid json -> returns None
    monkeypatch.setattr(
        core_redis,
        "redis_client",
        types.SimpleNamespace(get=lambda k: "not-json", expire=lambda *a, **k: None),
    )
    assert core_redis.get_session("s") is None

    # valid json -> returns dict and calls expire
    called = {}

    def fake_get(k):
        return json.dumps({"a": 1})

    def fake_expire(k, ttl):
        called["args"] = (k, ttl)

    monkeypatch.setattr(
        core_redis,
        "redis_client",
        types.SimpleNamespace(get=fake_get, expire=fake_expire),
    )
    res = core_redis.get_session("s1")
    assert res == {"a": 1}
    assert called["args"][0].endswith("s1")


def test_env_flag_default_and_true(monkeypatch):
    # when env var absent -> default is returned
    monkeypatch.delenv("SOME_TEST_VAR", raising=False)
    assert _env_flag("SOME_TEST_VAR", default=True) is True
    assert _env_flag("SOME_TEST_VAR", default=False) is False

    # truthy values
    monkeypatch.setenv("SOME_TEST_VAR", "1")
    assert _env_flag("SOME_TEST_VAR") is True
    monkeypatch.setenv("SOME_TEST_VAR", "yes")
    assert _env_flag("SOME_TEST_VAR") is True


def test_jira_helpers_ensure_sid_and_client_from_session(monkeypatch):
    from app.routes import jira as jira_mod

    # ensure_sid simply forwards
    class Req:
        pass

    class Resp:
        pass

    monkeypatch.setattr(jira_mod, "ensure_session", lambda req, resp: "sidv")
    assert jira_mod._ensure_sid(Req(), Resp()) == "sidv"

    # _jira_client_from_session raises when no entry for cloud
    session = {
        "tokens_by_cloud": {},
        "cloud_ids": ["c1"],
        "active_cloud_id": "c1",
        "access_token": "tok",
    }
    req = types.SimpleNamespace(query_params={})
    with pytest.raises(HTTPException) as e:
        jira_mod._jira_client_from_session(session, req)
    assert e.value.status_code == 401


def test_root_redirects_to_ui():
    from app.main import create_app

    app = create_app()
    from fastapi.testclient import TestClient

    local_client = TestClient(app)
    r = local_client.get("/", follow_redirects=False)
    # FastAPI root returns a redirect to /ui without following
    assert r.status_code in (307, 308)
    assert r.headers.get("location") == "/ui"
