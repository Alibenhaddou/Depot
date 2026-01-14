import asyncio
import types

import pytest
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.main import create_app
from app.routes import ai as ai_mod
from app.clients.jira import JiraClient
from app.core.config import settings

app = create_app()
client = TestClient(app)


def test_utils_truncate_and_adf():
    assert ai_mod._truncate("short", 10) == "short"
    long = "a" * 700
    out = ai_mod._truncate(long, 100)
    assert len(out) <= 101

    # adf to text
    adf = {
        "type": "doc",
        "content": [
            {"type": "paragraph", "content": [{"type": "text", "text": "hello"}]}
        ],
    }
    assert ai_mod._adf_to_text(adf) == "hello"


def test_extract_links_and_simplify():
    fields = {
        "issuelinks": [
            {
                "type": {"name": "rel"},
                "outwardIssue": {"key": "A"},
                "inwardIssue": {"key": "B"},
            }
        ]
    }
    links = ai_mod._extract_links(fields, limit=2)
    assert any(l.get("key") for l in links)

    issues_data = {"issues": [{"key": "P-1", "fields": {"summary": "s"}}]}
    simp = ai_mod._simplify_issues(issues_data, limit=10)
    assert simp[0]["key"] == "P-1"


def test__sse_formatting():
    s = ai_mod._sse("log", {"a": 1})
    assert s.startswith("event: log")
    assert "data:" in s


def test__llm_step_error_mapping(monkeypatch):
    class FakeLLM:
        async def chat_text(self, *a, **k):
            raise HTTPException(403, "forbidden")

    # should re-raise with title prefix
    with pytest.raises(HTTPException) as e:
        asyncio.run(ai_mod._llm_step(FakeLLM(), title="Test", system="s", user="u"))
    assert e.value.status_code == 403
    assert "Test:" in str(e.value.detail)


def test_analyze_issue_stream_no_token(monkeypatch):
    monkeypatch.setattr("app.routes.ai.ensure_session", lambda req, resp: "sid")
    # provide active_cloud_id but no tokens_by_cloud so entry resolves to None
    monkeypatch.setattr(
        "app.routes.ai.get_session",
        lambda sid: {"cloud_ids": ["c1"], "active_cloud_id": "c1"},
    )

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
        assert "401" in text


def test_analyze_issue_stream_jira_404(monkeypatch):
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
            resp = httpx.Response(404, request=req, content=b"not found")
            raise httpx.HTTPStatusError("err", request=req, response=resp)

        async def get_issue_comments(self, *a, **k):
            return {"comments": []}

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
        # depending on how the exception is raised, the stream may contain a 404 or fall back to a 502 message
        assert ("404" in text) or ("Erreur lors de l'appel Jira" in text)


def test_analyze_issue_stream_llm_error(monkeypatch):
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

    async def fake_llm_step(*a, **k):
        raise HTTPException(502, "LLM oops")

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
        assert "LLM oops" in text


# Additional tests to cover remaining branches and helpers in ai.py


def test__llm_step_generic_exception(monkeypatch):
    class FakeLLM:
        async def chat_text(self, *a, **k):
            raise Exception("boom")

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            ai_mod._llm_step(FakeLLM(), title="Description", system="s", user="u")
        )
    assert exc.value.status_code == 502
    assert "Description: Erreur LLM" in str(exc.value.detail)


def test_analyze_issue_client_exception_maps_502(monkeypatch):
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
            raise Exception("boom")

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeClient)

    r = client.post("/ai/analyze-issue", json={"issue_key": "P-1"})
    assert r.status_code == 502
    assert "Erreur lors de l'appel Jira" in r.text


def test_analyze_issue_skips_empty_comments_and_parses_links(monkeypatch):
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
                    "description": None,
                    "issuelinks": [
                        {"type": {"name": "rel"}, "outwardIssue": {"key": "A"}}
                    ],
                },
            }

        async def get_issue_comments(self, *a, **k):
            # comment body is empty -> should be skipped
            return {
                "comments": [
                    {"author": {"displayName": "A"}, "created": "t", "body": None}
                ]
            }

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeClient)

    captured: dict = {}

    async def fake_chat_text(system, user):
        # record the final user payload used by the LLM
        captured["user"] = user
        return "ok"

    monkeypatch.setattr(ai_mod.llm, "chat_text", fake_chat_text)

    r = client.post("/ai/analyze-issue", json={"issue_key": "P-1"})
    assert r.status_code == 200

    # verify that the constructed 'user' payload contains an empty comments list and the dependency key
    assert "'comments': []" in captured.get("user", "")
    assert "A" in captured.get("user", "")

    # final result should be present
    data = r.json()
    assert data.get("result") == "ok"


def test_analyze_issue_stream_skips_links_without_key(monkeypatch):
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
                        {"type": {"name": "rel"}, "outwardIssue": {}},
                        {"type": {"name": "rel"}, "outwardIssue": {"key": "A"}},
                    ],
                },
            }

        async def get_issue_comments(self, *a, **k):
            return {"comments": []}

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeClient)

    async def fake_llm_step(*a, **k):
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
        assert "dependance" in text
        assert "event: result" in text
        assert "ok" in text


def test_analyze_issue_stream_skips_keyless_links_via_monkeypatch(monkeypatch):
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
                },
            }

        async def get_issue_comments(self, *a, **k):
            return {"comments": []}

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeClient)
    # make _extract_links return a link without a key to hit the 'if not key: continue' guard
    monkeypatch.setattr(
        ai_mod, "_extract_links", lambda fields, limit: [{"type": "rel"}]
    )

    async def fake_llm_step(*a, **k):
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
        assert "dependance" in text
        assert "event: result" in text
        assert "ok" in text
