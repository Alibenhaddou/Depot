import types

from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import create_app
from app.routes import ai as ai_mod

app = create_app()
client = TestClient(app)


def test_summarize_jql_no_entry(monkeypatch):
    monkeypatch.setattr("app.routes.ai.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.ai.get_session", lambda sid: {})

    r = client.post("/ai/summarize-jql", json={"jql": "x"})
    # select_cloud_id raises 400 when no clouds are connected
    assert r.status_code == 400


def test_summarize_jql_search_permission(monkeypatch):
    # search_jql raising a generic Exception -> 502 path
    monkeypatch.setattr("app.routes.ai.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr(
        "app.routes.ai.get_session",
        lambda sid: {
            "tokens_by_cloud": {"c1": {"access_token": "t1"}},
            "cloud_ids": ["c1"],
            "active_cloud_id": "c1",
        },
    )

    class FakeClientErr:
        def __init__(self, *a, **k):
            pass

        async def search_jql(self, *a, **k):
            raise Exception("boom")

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeClientErr)

    r = client.post("/ai/summarize-jql", json={"jql": "x"})
    assert r.status_code == 502


def test_analyze_issue_no_entry(monkeypatch):
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

        async def search_jql(self, *a, **k):
            raise PermissionError()

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeClient)

    r = client.post("/ai/summarize-jql", json={"jql": "x"})
    assert r.status_code == 401


def test_analyze_issue_no_entry(monkeypatch):
    monkeypatch.setattr("app.routes.ai.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.ai.get_session", lambda sid: {})

    r = client.post("/ai/analyze-issue", json={"issue_key": "P-1"})
    # select_cloud_id raises 400 when no clouds are connected
    assert r.status_code == 400


def test_analyze_issue_entry_missing_tokens(monkeypatch):
    monkeypatch.setattr("app.routes.ai.ensure_session", lambda req, resp: "sid")
    # active cloud present but tokens_by_cloud entry missing
    monkeypatch.setattr(
        "app.routes.ai.get_session",
        lambda sid: {
            "cloud_ids": ["c1"],
            "active_cloud_id": "c1",
            "tokens_by_cloud": {},
        },
    )

    r = client.post("/ai/analyze-issue", json={"issue_key": "P-1"})
    assert r.status_code == 401


def test_analyze_issue_llm_generic_exception(monkeypatch):
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
        raise Exception("llm boom")

    monkeypatch.setattr(ai_mod.llm, "chat_text", fake_chat)

    r = client.post("/ai/analyze-issue", json={"issue_key": "P-1"})
    assert r.status_code == 502


def test_analyze_issue_success_returns_llm(monkeypatch):
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
            return {
                "comments": [
                    {
                        "author": {"displayName": "A"},
                        "created": "t",
                        "body": {"type": "text", "text": "c"},
                    }
                ]
            }

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeClient)

    async def fake_chat(*, system, user):
        return "final-text"

    monkeypatch.setattr(ai_mod.llm, "chat_text", fake_chat)

    r = client.post("/ai/analyze-issue", json={"issue_key": "P-1"})
    assert r.status_code == 200
    assert r.json()["result"] == "final-text"


def test_analyze_issue_stream_inspects_dependances_and_calls_llm(monkeypatch):
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
            return {
                "key": "P-1",
                "fields": {
                    "summary": "s",
                    "description": {
                        "type": "doc",
                        "content": [{"type": "text", "text": "desc"}],
                    },
                    "issuelinks": [
                        {"type": {"name": "rel"}, "outwardIssue": {"key": "A"}},
                        {"type": {"name": "rel"}, "inwardIssue": {"key": "B"}},
                    ],
                },
            }

        async def get_issue_comments(self, *a, **k):
            return {
                "comments": [
                    {
                        "author": {"displayName": "A"},
                        "created": "t",
                        "body": {"type": "text", "text": "c1"},
                    },
                    {
                        "author": {"displayName": "B"},
                        "created": "t2",
                        "body": {"type": "text", "text": "c2"},
                    },
                ]
            }

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeClient)

    calls = []

    async def fake_llm_step(client, *, title, system, user):
        calls.append((title, user))
        return f"res-{title}"

    monkeypatch.setattr(ai_mod, "_llm_step", fake_llm_step)

    with client.stream(
        "POST", "/ai/analyze-issue/stream", json={"issue_key": "P-1"}
    ) as resp:
        text = "\n".join(
            [
                line.decode() if isinstance(line, bytes) else line
                for line in resp.iter_lines()
            ]
        )
        assert "event: result" in text
        assert "res-Synthese" in text

    # ensure Dependances call was made and user contains 'Dependances:'
    assert any(t == "Dependances" and "Dependances:" in u for t, u in calls)
