import types
import httpx
import asyncio

import pytest

from app.clients.jira import JiraClient, select_cloud_id


class DummyResponse:
    def __init__(self, status_code=200, text="", json_data=None):
        self.status_code = status_code
        self._text = text
        self._json = json_data or {}
        self.request = types.SimpleNamespace(url="http://test")

    @property
    def text(self):
        return self._text

    def json(self):
        return self._json


class FakeClient:
    def __init__(self):
        self.requests = []

    async def request(
        self, method=None, url=None, headers=None, params=None, json=None
    ):
        self.requests.append((method, url, headers, params, json))
        return DummyResponse(json_data={"ok": True})


def test_headers_and_base_url():
    c = JiraClient("tok", "cloud-1")
    assert "Authorization" in c._headers
    assert c._ex_base_url.endswith("/rest/api/3")


def test_request_raises_permission_error(monkeypatch):
    c = JiraClient("tok", "cloud-1")

    async def request(*a, **k):
        return types.SimpleNamespace(status_code=401, text="", request=None)

    fake = types.SimpleNamespace(request=request)
    monkeypatch.setattr(c, "_client", fake)
    with pytest.raises(PermissionError):
        asyncio.run(c._request("GET", "/x"))


def test_request_raises_httpx_error(monkeypatch):
    c = JiraClient("tok", "cloud-1")

    class BadResp:
        status_code = 500
        text = "server failure"
        request = None

    async def request(*a, **k):
        return BadResp()

    fake = types.SimpleNamespace(request=request)
    monkeypatch.setattr(c, "_client", fake)
    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(c._request("GET", "/x"))


def test_search_jql_fallback(monkeypatch):
    c = JiraClient("tok", "cloud-1")

    # first call raises HTTPStatusError with 404
    class Resp404:
        status_code = 404
        text = "not found"
        request = None

    async def first_request(*a, **k):
        err = httpx.HTTPStatusError(message="err", request=None, response=Resp404())
        raise err

    async def second_request(*a, **k):
        return {"ok": True}

    # monkeypatch _request to behave like first failing then succeeding
    calls = {"n": 0}

    async def fake_request(method, path, **k):
        calls["n"] += 1
        if calls["n"] == 1:
            err = httpx.HTTPStatusError(message="err", request=None, response=Resp404())
            raise err
        return await second_request()

    monkeypatch.setattr(c, "_request", fake_request)

    out = asyncio.run(c.search_jql("project = X"))
    assert out == {"ok": True}


def test_select_cloud_id_priority_and_errors():
    session = {
        "tokens_by_cloud": {"a": 1, "b": 2},
        "cloud_ids": ["a", "b"],
        "active_cloud_id": "b",
    }
    req = types.SimpleNamespace(query_params={})
    # no query param -> active wins
    assert select_cloud_id(session, req) == "b"

    # explicit override
    req = types.SimpleNamespace(query_params={"cloud_id": "a"})
    assert select_cloud_id(session, req) == "a"

    # unknown cloud_id -> raises
    req = types.SimpleNamespace(query_params={"cloud_id": "zzz"})
    with pytest.raises(Exception):
        select_cloud_id(session, req)

    # empty session
    with pytest.raises(Exception):
        select_cloud_id({}, types.SimpleNamespace(query_params={}))
