import asyncio

from app.clients.jira import JiraClient


def test_get_myself_calls_request(monkeypatch):
    c = JiraClient("tok", "cloud-1")
    calls = {}

    async def fake_request(method, path, **_kwargs):
        calls["method"] = method
        calls["path"] = path
        return {"accountId": "acct"}

    monkeypatch.setattr(c, "_request", fake_request)

    out = asyncio.run(c.get_myself())
    assert out == {"accountId": "acct"}
    assert calls["method"] == "GET"
    assert calls["path"] == "/myself"
