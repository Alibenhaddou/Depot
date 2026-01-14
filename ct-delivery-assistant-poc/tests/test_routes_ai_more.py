import asyncio

import httpx
import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import create_app
from app.routes import ai as ai_mod

app = create_app()
client = TestClient(app)


def test_summarize_jql_llm_generic_exception(monkeypatch):
    monkeypatch.setattr("app.routes.ai.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.ai.get_session", lambda sid: {"tokens_by_cloud": {"c1": {"access_token": "t1"}}, "cloud_ids": ["c1"], "active_cloud_id": "c1"})

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def search_jql(self, *a, **k):
            return {"issues": []}

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeClient)

    async def fake_chat(system, user):
        raise Exception("boom")

    monkeypatch.setattr(ai_mod.llm, "chat_json", fake_chat)

    r = client.post("/ai/summarize-jql", json={"jql": "x"})
    assert r.status_code == 502


def test_summarize_jql_llm_http_exception(monkeypatch):
    monkeypatch.setattr("app.routes.ai.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.ai.get_session", lambda sid: {"tokens_by_cloud": {"c1": {"access_token": "t1"}}, "cloud_ids": ["c1"], "active_cloud_id": "c1"})

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def search_jql(self, *a, **k):
            return {"issues": []}

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeClient)

    async def fake_chat(system, user):
        raise HTTPException(502, "LLM error")

    monkeypatch.setattr(ai_mod.llm, "chat_json", fake_chat)

    r = client.post("/ai/summarize-jql", json={"jql": "x"})
    assert r.status_code == 502


def test_analyze_issue_404(monkeypatch):
    monkeypatch.setattr("app.routes.ai.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.ai.get_session", lambda sid: {"tokens_by_cloud": {"c1": {"access_token": "t1"}}, "cloud_ids": ["c1"], "active_cloud_id": "c1"})

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def get_issue(self, *a, **k):
            req = httpx.Request("GET", "http://x")
            resp = httpx.Response(404, request=req, content=b"not found")
            raise httpx.HTTPStatusError("err", request=req, response=resp)

        async def get_issue_comments(self, *a, **k):
            return {"comments": []}

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeClient)

    r = client.post("/ai/analyze-issue", json={"issue_key": "P-1"})
    assert r.status_code == 404


def test_analyze_issue_stream_success_with_links(monkeypatch):
    monkeypatch.setattr("app.routes.ai.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.ai.get_session", lambda sid: {"tokens_by_cloud": {"c1": {"access_token": "t1"}}, "cloud_ids": ["c1"], "active_cloud_id": "c1"})

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def get_issue(self, *a, **k):
            return {
                "key": "P-1",
                "fields": {
                    "summary": "s",
                    "description": {"type": "doc", "content": [{"type": "text", "text": "desc"}]},
                    "issuelinks": [{"type": {"name": "rel"}, "outwardIssue": {"key": "A"}}],
                },
            }

        async def get_issue_comments(self, *a, **k):
            return {"comments": [{"author": {"displayName": "A"}, "created": "t", "body": {"type": "text", "text": "c"}}]}

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeClient)

    async def fake_llm_step(*a, **k):
        return "ok-summary"

    monkeypatch.setattr(ai_mod, "_llm_step", fake_llm_step)

    with client.stream("POST", "/ai/analyze-issue/stream", json={"issue_key": "P-1"}) as resp:
        text = "\n".join([line.decode() if isinstance(line, bytes) else line for line in resp.iter_lines()])
        assert "dependance" in text or "dependance(s)" in text or "dependance(s) detectee" in text
        assert "event: result" in text
        assert "ok-summary" in text


def test_adf_to_text_fallback():
    assert ai_mod._adf_to_text(None, fallback="f") == "f"
