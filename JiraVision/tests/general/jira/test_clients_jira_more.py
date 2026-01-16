import asyncio
import types

import pytest

from app.clients.jira import JiraClient


def test_search_jql_passes_next_page_token(monkeypatch):
    jc = JiraClient("t", "cid")

    async def fake_request(self, method, path, params=None, json_body=None):
        assert json_body.get("nextPageToken") == "tok"
        return {"issues": []}

    monkeypatch.setattr(JiraClient, "_request", fake_request)

    res = asyncio.run(jc.search_jql("x", next_page_token="tok"))
    assert "issues" in res


def test_request_401_raises_permission_error(monkeypatch):
    jc = JiraClient("t", "cid")

    async def fake_request(method, url, headers=None, params=None, json=None):
        return types.SimpleNamespace(status_code=401, text="", request=None)

    # monkeypatch the underlying low-level client.request to return a 401 response
    class FakeClient:
        async def request(self, *a, **k):
            return types.SimpleNamespace(
                status_code=401, text="", request=types.SimpleNamespace()
            )

    jc._client = FakeClient()

    with pytest.raises(PermissionError):
        asyncio.run(jc._request("GET", "/issue/x"))
