import asyncio
import types

import httpx
import pytest

from app.clients.jira import JiraClient, select_cloud_id
from fastapi import HTTPException


class DummyResp:
    def __init__(self, status=200, json_data=None, text=""):
        self.status_code = status
        self._json = json_data or {}
        self.text = text
        self.request = types.SimpleNamespace(url="http://test")

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            req = httpx.Request("POST", "http://test")
            resp = httpx.Response(
                self.status_code, request=req, content=(self.text or "").encode()
            )
            raise httpx.HTTPStatusError("err", request=req, response=resp)


def test_search_jql_fallback(monkeypatch):
    jc = JiraClient("t", "cid")

    calls = {"n": 0}

    async def fake_request(self, method, path, params=None, json_body=None):
        calls["n"] += 1
        if calls["n"] == 1:
            req = httpx.Request("POST", "http://test")
            resp = httpx.Response(404, request=req, content=b"not found")
            raise httpx.HTTPStatusError("err", request=req, response=resp)
        return {"issues": []}

    monkeypatch.setattr(JiraClient, "_request", fake_request)

    res = asyncio.run(jc.search_jql("x"))
    assert "issues" in res


def test_select_cloud_id_invalid_requested():
    req = types.SimpleNamespace(query_params={"cloud_id": "b"})
    with pytest.raises(HTTPException):
        select_cloud_id({"cloud_ids": ["a"]}, req)


def test_select_cloud_id_derive_from_tokens():
    req = types.SimpleNamespace(query_params={})
    sid = select_cloud_id({"tokens_by_cloud": {"a": {}}, "cloud_ids": []}, req)
    assert sid == "a"


def test_select_cloud_id_no_clouds():
    req = types.SimpleNamespace(query_params={})
    with pytest.raises(HTTPException):
        select_cloud_id({}, req)


def test_get_issue_comments_clamps(monkeypatch):
    jc = JiraClient("t", "cid")

    async def fake_req(self, method, path, params=None, json_body=None):
        # ensure params forwarded
        assert params == {"maxResults": 1}
        return {"comments": []}

    monkeypatch.setattr(JiraClient, "_request", fake_req)
    res = asyncio.run(jc.get_issue_comments("P-1", max_results=0))
    assert "comments" in res


def test__request_returns_json_and_aclose(monkeypatch):
    jc = JiraClient("t", "cid")

    async def fake_request(method=None, url=None, headers=None, params=None, json=None):
        return DummyResp(status=200, json_data={"ok": True}, text="")

    # attach fake request and aclose implementation
    closed = []

    async def fake_aclose():
        closed.append(True)

    fake_client = types.SimpleNamespace(request=fake_request, aclose=fake_aclose)
    monkeypatch.setattr(jc, "_client", fake_client)

    res = asyncio.run(jc._request("GET", "/x"))
    assert res == {"ok": True}

    asyncio.run(jc.aclose())
    assert closed == [True]


def test_search_jql_reraises_on_non_fallback_status(monkeypatch):
    jc = JiraClient("t", "cid")

    async def bad_request(method, path, params=None, json_body=None):
        req = httpx.Request("POST", "http://x")
        resp = httpx.Response(500, request=req, content=b"server")
        raise httpx.HTTPStatusError("err", request=req, response=resp)

    monkeypatch.setattr(JiraClient, "_request", bad_request)

    with pytest.raises(httpx.HTTPStatusError):
        asyncio.run(jc.search_jql("x"))
