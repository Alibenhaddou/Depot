import httpx

from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import create_app
from app.routes import ai as ai_mod

app = create_app()
client = TestClient(app)


def test_simplify_issues_truncation():
    long = "x" * 400
    data = {"issues": [{"key": "P-1", "fields": {"summary": long}}]}
    out = ai_mod._simplify_issues(data, limit=10)
    assert out[0]["summary"].endswith("…")


def test_extract_links_limit_and_missing_key():
    fields = {"issuelinks": [{"outwardIssue": {"key": "A"}}, {"inwardIssue": {}}]}
    links = ai_mod._extract_links(fields, limit=1)
    assert len(links) == 1
    assert links[0]["key"] == "A"


def test_analyze_issue_permission_error(monkeypatch):
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

    r = client.post("/ai/analyze-issue", json={"issue_key": "P-1"})
    assert r.status_code == 401


def test_analyze_issue_http_error_500(monkeypatch):
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
            req = httpx.Request("GET", "http://x")
            resp = httpx.Response(500, request=req, content=b"err")
            raise httpx.HTTPStatusError("err", request=req, response=resp)

        async def get_issue_comments(self, *a, **k):
            return {"comments": []}

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeClient)

    r = client.post("/ai/analyze-issue", json={"issue_key": "P-1"})
    assert r.status_code == 502


def test_analyze_issue_stream_final_synth_error(monkeypatch):
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
                    "description": {"type": "text", "text": "d"},
                },
            }

        async def get_issue_comments(self, *a, **k):
            return {"comments": []}

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeClient)

    # first calls return OK, final call raises HTTPException
    async def fake_llm_step(client, *, title, system, user):
        if title == "Synthese":
            raise HTTPException(502, "Synth error")
        return "ok"

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
        assert "event: error" in text
        assert "Synth error" in text
