import asyncio
import types

import httpx
import pytest

from app.clients.jira import JiraClient, select_cloud_id


def test_request_snippet_newlines(monkeypatch):
    jc = JiraClient("t", "cid")

    class FakeClient:
        async def request(self, *a, **k):
            return types.SimpleNamespace(
                status_code=500, text="line1\nline2", request=types.SimpleNamespace()
            )

    jc._client = FakeClient()

    with pytest.raises(httpx.HTTPStatusError) as e:
        asyncio.run(jc._request("GET", "/x"))
    assert "line1 line2" in str(e.value)


def test_search_jql_fallback_410(monkeypatch):
    jc = JiraClient("t", "cid")

    calls = {"n": 0}

    async def fake_request(self, method, path, params=None, json_body=None):
        calls["n"] += 1
        if calls["n"] == 1:
            req = httpx.Request("POST", "http://test")
            resp = httpx.Response(410, request=req, content=b"gone")
            raise httpx.HTTPStatusError("err", request=req, response=resp)
        return {"issues": []}

    monkeypatch.setattr(JiraClient, "_request", fake_request)

    res = asyncio.run(jc.search_jql("x"))
    assert "issues" in res


def test_select_cloud_id_requested_valid():
    req = types.SimpleNamespace(query_params={"cloud_id": "b"})
    sid = select_cloud_id({"cloud_ids": ["b", "c"]}, req)
    assert sid == "b"


def test_get_issue_with_expand_passes_params(monkeypatch):
    jc = JiraClient("t", "cid")

    async def fake_request(self, method, path, params=None, json_body=None):
        assert params == {"expand": "renderedFields"}
        return {"key": "P-1"}

    monkeypatch.setattr(JiraClient, "_request", fake_request)

    res = asyncio.run(jc.get_issue("P-1", expand="renderedFields"))
    assert res.get("key") == "P-1"
