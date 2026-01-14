import httpx

from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import create_app
from app.routes import ai as ai_mod

app = create_app()
client = TestClient(app)


def test_summarize_jql_permission_error(monkeypatch):
    monkeypatch.setattr("app.routes.ai.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.ai.get_session", lambda sid: {"tokens_by_cloud": {"c1": {"access_token": "t1"}}, "cloud_ids": ["c1"], "active_cloud_id": "c1"})

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def search_jql(self, *a, **k):
            raise PermissionError()

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeClient)

    r = client.post("/ai/summarize-jql", json={"jql": "x"})
    assert r.status_code == 401
    assert "Token expiré" in r.text or "Token" in r.text


def test_analyze_issue_http500_message(monkeypatch):
    monkeypatch.setattr("app.routes.ai.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.ai.get_session", lambda sid: {"tokens_by_cloud": {"c1": {"access_token": "t1"}}, "cloud_ids": ["c1"], "active_cloud_id": "c1"})

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def get_issue(self, *a, **k):
            req = httpx.Request("GET", "http://x")
            resp = httpx.Response(500, request=req, content=b"err")
            raise httpx.HTTPStatusError("err", request=req, response=resp)

        async def get_issue_comments(self, *a, **k):
            return {"comments": []}

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeClient)

    r = client.post("/ai/analyze-issue", json={"issue_key": "P-1"})
    assert r.status_code == 502
    assert "Erreur lors de l'appel Jira" in r.text


def test_analyze_issue_stream_404_and_empty_comment(monkeypatch):
    monkeypatch.setattr("app.routes.ai.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.ai.get_session", lambda sid: {"tokens_by_cloud": {"c1": {"access_token": "t1"}}, "cloud_ids": ["c1"], "active_cloud_id": "c1"})

    # 404 case
    class Fake404:
        def __init__(self, *a, **k):
            pass

        async def get_issue(self, *a, **k):
            req = httpx.Request("GET", "http://x")
            resp = httpx.Response(404, request=req, content=b"not found")
            raise httpx.HTTPStatusError("err", request=req, response=resp)

        async def get_issue_comments(self, *a, **k):
            return {"comments": []}

    monkeypatch.setattr("app.routes.ai.JiraClient", Fake404)

    with client.stream("POST", "/ai/analyze-issue/stream", json={"issue_key": "P-1"}) as resp:
        text = "\n".join([line.decode() if isinstance(line, bytes) else line for line in resp.iter_lines()])
        assert "event: error" in text
        assert "Ticket introuvable" in text

    # empty comment in stream should be skipped
    class FakeClient2:
        def __init__(self, *a, **k):
            pass

        async def get_issue(self, *a, **k):
            return {"key": "P-1", "fields": {"summary": "s", "description": "d"}}

        async def get_issue_comments(self, *a, **k):
            return {"comments": [{"author": {"displayName": "A"}, "created": "t", "body": {}}]}

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeClient2)

    async def fake_llm_step(*a, **k):
        return "ok"

    monkeypatch.setattr(ai_mod, "_llm_step", fake_llm_step)

    with client.stream("POST", "/ai/analyze-issue/stream", json={"issue_key": "P-1"}) as resp:
        text = "\n".join([line.decode() if isinstance(line, bytes) else line for line in resp.iter_lines()])
        # ensure it reaches result despite empty comment
        assert "event: result" in text


def test_stream_llm_http_exception_propagates(monkeypatch):
    monkeypatch.setattr("app.routes.ai.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.ai.get_session", lambda sid: {"tokens_by_cloud": {"c1": {"access_token": "t1"}}, "cloud_ids": ["c1"], "active_cloud_id": "c1"})

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def get_issue(self, *a, **k):
            return {"key": "P-1", "fields": {"summary": "s", "description": "d"}}

        async def get_issue_comments(self, *a, **k):
            return {"comments": []}

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeClient)

    async def fake_llm_step(*a, **k):
        raise HTTPException(502, "LLM failed")

    monkeypatch.setattr(ai_mod, "_llm_step", fake_llm_step)

    with client.stream("POST", "/ai/analyze-issue/stream", json={"issue_key": "P-1"}) as resp:
        text = "\n".join([line.decode() if isinstance(line, bytes) else line for line in resp.iter_lines()])
        assert "event: error" in text
        assert "LLM failed" in text
