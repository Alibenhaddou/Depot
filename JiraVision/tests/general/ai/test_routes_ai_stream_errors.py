import httpx

from fastapi.testclient import TestClient

from app.main import create_app

app = create_app()
client = TestClient(app)


def test_analyze_issue_stream_jira_500_maps_to_502(monkeypatch):
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
        assert "502" in text
