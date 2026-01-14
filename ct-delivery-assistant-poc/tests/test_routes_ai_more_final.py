import httpx

from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import create_app
from app.routes import ai as ai_mod

app = create_app()
client = TestClient(app)


def test_summarize_jql_entry_missing(monkeypatch):
    monkeypatch.setattr("app.routes.ai.ensure_session", lambda req, resp: "sid")
    # active_cloud_id exists but tokens_by_cloud has no entry for it
    monkeypatch.setattr(
        "app.routes.ai.get_session",
        lambda sid: {
            "cloud_ids": ["c1"],
            "active_cloud_id": "c1",
            "tokens_by_cloud": {},
        },
    )

    r = client.post("/ai/summarize-jql", json={"jql": "x"})
    assert r.status_code == 401


def test_analyze_issue_llm_http_exception_propagates(monkeypatch):
    monkeypatch.setattr("app.routes.ai.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr(
        "app.routes.ai.get_session",
        lambda sid: {
            "tokens_by_cloud": {"c1": {"access_token": "t1"}},
            "cloud_ids": ["c1"],
            "active_cloud_id": "c1",
        },
    )

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def get_issue(self, *a, **k):
            return {"key": "P-1", "fields": {"summary": "s", "description": "d"}}

        async def get_issue_comments(self, *a, **k):
            return {"comments": []}

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeClient)

    async def fake_chat(*, system, user):
        raise HTTPException(418, "teapot")

    monkeypatch.setattr(ai_mod.llm, "chat_text", fake_chat)

    r = client.post("/ai/analyze-issue", json={"issue_key": "P-1"})
    assert r.status_code == 418


def test_analyze_issue_stream_permission_error(monkeypatch):
    monkeypatch.setattr("app.routes.ai.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr(
        "app.routes.ai.get_session",
        lambda sid: {
            "tokens_by_cloud": {"c1": {"access_token": "t1"}},
            "cloud_ids": ["c1"],
            "active_cloud_id": "c1",
        },
    )

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def get_issue(self, *a, **k):
            raise PermissionError()

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeClient)

    with client.stream(
        "POST", "/ai/analyze-issue/stream", json={"issue_key": "P-1"}
    ) as resp:
        text = "\n".join(
            [
                line.decode() if isinstance(line, bytes) else line
                for line in resp.iter_lines()
            ]
        )
        assert "event: error" in text
        assert "Token expiré" in text
