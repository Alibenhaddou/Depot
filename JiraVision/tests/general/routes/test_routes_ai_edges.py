import types
from fastapi.testclient import TestClient

from app.main import create_app

app = create_app()
client = TestClient(app)


def test_analyze_issue_skips_empty_comment_and_builds_deps(monkeypatch):
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
                        {"type": {"name": "rel"}, "outwardIssue": {"key": "A"}}
                    ],
                },
            }

        async def get_issue_comments(self, *a, **k):
            # comment body that yields empty text -> should be skipped
            return {
                "comments": [
                    {"author": {"displayName": "A"}, "created": "t", "body": {}}
                ]
            }

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeClient)

    async def fake_chat(system, user):
        return "final-text"

    monkeypatch.setattr("app.routes.ai.llm", types.SimpleNamespace(chat_text=fake_chat))

    r = client.post("/ai/analyze-issue", json={"issue_key": "P-1"})
    assert r.status_code == 200
    assert r.json()["result"] == "final-text"
