import types

from fastapi.testclient import TestClient

from app.main import create_app

app = create_app()
client = TestClient(app)


# ------------------------- Helper fakes ---------------------------------
class DummyResp:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text
        self.request = types.SimpleNamespace(url="http://test")

    def json(self):
        return self._json


class FakeJiraClient:
    def __init__(self, access_token=None, cloud_id=None):
        self.access_token = access_token
        self.cloud_id = cloud_id

    async def aclose(self):
        return None

    async def get_issue(self, issue_key: str, *, expand=None):
        return {
            "key": issue_key,
            "fields": {
                "summary": "S",
                "status": {"name": "Open"},
                "issuetype": {"name": "Bug"},
                "project": {"key": "P"},
            },
        }

    async def get_issue_comments(self, issue_key: str, max_results: int = 20):
        return {
            "comments": [
                {
                    "author": {"displayName": "A"},
                    "created": "t",
                    "body": {"type": "doc", "content": [{"type": "text", "text": "c"}]},
                }
            ]
        }

    async def search_jql(
        self, jql: str, max_results: int = 20, next_page_token: str | None = None
    ):
        return {
            "issues": [
                {
                    "key": "P-1",
                    "fields": {
                        "summary": "sum",
                        "status": {"name": "Open"},
                        "issuetype": {"name": "Task"},
                        "project": {"key": "P"},
                    },
                }
            ]
        }


class FakeLLM:
    def __init__(self):
        pass

    async def chat_json(self, system: str, user: str):
        return {"summary": "ok"}

    async def chat_text(self, system: str, user: str):
        return "analysis text"


# ------------------------- Auth routes ---------------------------------


def test_login_sets_state_and_cookie(monkeypatch):
    # stub session helpers
    monkeypatch.setattr("app.routes.auth.ensure_session", lambda req, resp: "sid-login")

    captured = {}

    def fake_set_session(sid, sess):
        captured["sid"] = sid
        captured["sess"] = sess

    monkeypatch.setattr("app.routes.auth.set_session", fake_set_session)
    monkeypatch.setattr("app.routes.auth.get_session", lambda sid: {})

    r = client.get("/login", follow_redirects=False)
    assert r.status_code in (307, 302)
    # oauth_state cookie should be set
    cookies = r.headers.get_list("set-cookie")
    assert any("oauth_state" in c for c in cookies)
    assert captured["sid"] == "sid-login"
    assert "state" in captured["sess"]


def test_oauth_callback_success(monkeypatch):
    # prepare session with state
    session = {"state": "s123"}
    monkeypatch.setattr("app.routes.auth.ensure_session", lambda req, resp: "sid-oauth")
    monkeypatch.setattr("app.routes.auth.get_session", lambda sid: session)

    # stub token exchange
    async def fake_post(*a, **k):
        return DummyResp(json_data={"access_token": "atok"})

    class FakeAsyncClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *a, **k):
            return await fake_post()

        async def get(self, *a, **k):
            return DummyResp(json_data=[])

        async def aclose(self):
            return None

    monkeypatch.setattr("app.routes.auth.httpx.AsyncClient", FakeAsyncClient)

    # stub accessible resources
    async def fake_accessible(token):
        return [
            {"id": "c1", "url": "https://x", "scopes": ["read:jira-work"], "name": "C1"}
        ]

    monkeypatch.setattr("app.routes.auth._get_accessible_resources", fake_accessible)

    # stub user info fetch
    async def fake_get_user_info(token, cloud_id):
        return {
            "accountId": "user123",
            "displayName": "Test User",
            "emailAddress": "test@example.com",
            "avatarUrls": {"48x48": "https://avatar.url"},
        }

    monkeypatch.setattr("app.routes.auth._get_user_info", fake_get_user_info)

    captured = {}

    def fake_set_session(sid, sess):
        captured["sess"] = sess

    monkeypatch.setattr("app.routes.auth.set_session", fake_set_session)

    r = client.get("/oauth/callback?code=code&state=s123", follow_redirects=False)
    assert r.status_code in (307, 302)
    assert captured["sess"]["tokens_by_cloud"]["c1"]["access_token"] == "atok"
    assert captured["sess"]["active_cloud_id"] == "c1"
    assert captured["sess"]["user_info"]["accountId"] == "user123"
    assert captured["sess"]["user_info"]["displayName"] == "Test User"


def test_oauth_callback_success_without_user_info(monkeypatch):
    """Test OAuth callback succeeds even if user info fetch fails."""
    # prepare session with state
    session = {"state": "s123"}
    monkeypatch.setattr("app.routes.auth.ensure_session", lambda req, resp: "sid-oauth")
    monkeypatch.setattr("app.routes.auth.get_session", lambda sid: session)

    # stub token exchange
    async def fake_post(*a, **k):
        return DummyResp(json_data={"access_token": "atok"})

    class FakeAsyncClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, *a, **k):
            return await fake_post()

        async def get(self, *a, **k):
            return DummyResp(json_data=[])

        async def aclose(self):
            return None

    monkeypatch.setattr("app.routes.auth.httpx.AsyncClient", FakeAsyncClient)

    # stub accessible resources
    async def fake_accessible(token):
        return [
            {"id": "c1", "url": "https://x", "scopes": ["read:jira-work"], "name": "C1"}
        ]

    monkeypatch.setattr("app.routes.auth._get_accessible_resources", fake_accessible)

    # stub user info fetch to return None (failure case)
    async def fake_get_user_info_fail(token, cloud_id):
        return None

    monkeypatch.setattr("app.routes.auth._get_user_info", fake_get_user_info_fail)

    captured = {}

    def fake_set_session(sid, sess):
        captured["sess"] = sess

    monkeypatch.setattr("app.routes.auth.set_session", fake_set_session)

    r = client.get("/oauth/callback?code=code&state=s123", follow_redirects=False)
    assert r.status_code in (307, 302)
    assert captured["sess"]["tokens_by_cloud"]["c1"]["access_token"] == "atok"
    assert captured["sess"]["active_cloud_id"] == "c1"
    # user_info should not be present when fetch fails
    assert "user_info" not in captured["sess"]


def test_oauth_callback_bad_state(monkeypatch):
    monkeypatch.setattr("app.routes.auth.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.auth.get_session", lambda sid: {})

    r = client.get("/oauth/callback?code=code&state=wrong", follow_redirects=False)
    assert r.status_code == 400


def test_logout_calls_destroy(monkeypatch):
    called = {"ok": False}
    monkeypatch.setattr(
        "app.routes.auth.destroy_session", lambda req, resp: called.update({"ok": True})
    )

    r = client.get("/logout", follow_redirects=False)
    assert r.status_code in (307, 302)
    assert called["ok"]


# ------------------------- Jira routes ---------------------------------


def test_jira_select_and_instances(monkeypatch):
    # session with cloud ids
    monkeypatch.setattr("app.routes.jira._ensure_sid", lambda req, resp: "sid-js")
    ses = {
        "cloud_ids": ["a", "b"],
        "active_cloud_id": "a",
        "jira_sites": [{"id": "a", "name": "A", "url": "u"}],
    }
    monkeypatch.setattr("app.routes.jira.get_session", lambda sid: ses)

    cap = {}

    def fake_set_session(sid, s):
        cap["s"] = s

    monkeypatch.setattr("app.routes.jira.set_session", fake_set_session)

    r = client.post("/jira/select", params={"cloud_id": "b"})
    assert r.status_code == 200
    assert r.json()["ok"]
    assert cap["s"]["active_cloud_id"] == "b"

    r2 = client.get("/jira/instances")
    assert r2.status_code == 200
    assert r2.json()["cloud_ids"] == ["a", "b"]


def test_jira_issue_and_search(monkeypatch):
    # session with valid token
    monkeypatch.setattr("app.routes.jira._ensure_sid", lambda req, resp: "sid-j1")
    ses = {
        "tokens_by_cloud": {"c1": {"access_token": "t1", "site_url": "u"}},
        "cloud_ids": ["c1"],
        "active_cloud_id": "c1",
    }
    monkeypatch.setattr("app.routes.jira.get_session", lambda sid: ses)

    # patch JiraClient to fake
    monkeypatch.setattr("app.routes.jira.JiraClient", FakeJiraClient)

    r = client.get("/jira/issue", params={"issue_key": "P-1"})
    assert r.status_code == 200
    data = r.json()
    assert data["issue_key"] == "P-1"

    r2 = client.get("/jira/search", params={"jql": "x"})
    assert r2.status_code == 200
    assert "issues" in r2.json()

    # invalid max_results
    r3 = client.get("/jira/search", params={"jql": "x", "max_results": 0})
    assert r3.status_code == 400


# ------------------------- AI routes ---------------------------------


def test_summarize_jql_success(monkeypatch):
    monkeypatch.setattr("app.routes.ai.ensure_session", lambda req, resp: "sid-ai")
    ses = {
        "tokens_by_cloud": {"c1": {"access_token": "t1"}},
        "cloud_ids": ["c1"],
        "active_cloud_id": "c1",
    }
    monkeypatch.setattr("app.routes.ai.get_session", lambda sid: ses)

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeJiraClient)
    monkeypatch.setattr("app.routes.ai.llm", FakeLLM())

    r = client.post("/ai/summarize-jql", json={"jql": "project = X", "max_results": 10})
    assert r.status_code == 200
    body = r.json()
    assert body["cloud_id"] == "c1"
    assert body["count"] >= 0
    assert body["result"]["summary"] == "ok"


def test_analyze_issue_and_stream(monkeypatch):
    monkeypatch.setattr("app.routes.ai.ensure_session", lambda req, resp: "sid-ai2")
    ses = {
        "tokens_by_cloud": {"c1": {"access_token": "t1"}},
        "cloud_ids": ["c1"],
        "active_cloud_id": "c1",
    }
    monkeypatch.setattr("app.routes.ai.get_session", lambda sid: ses)

    monkeypatch.setattr("app.routes.ai.JiraClient", FakeJiraClient)
    monkeypatch.setattr("app.routes.ai.llm", FakeLLM())

    r = client.post("/ai/analyze-issue", json={"issue_key": "P-1"})
    assert r.status_code == 200
    assert "result" in r.json()

    # streaming
    with client.stream(
        "POST", "/ai/analyze-issue/stream", json={"issue_key": "P-1"}
    ) as resp:
        assert resp.status_code == 200
        text = "\n".join(
            [
                line.decode() if isinstance(line, bytes) else line
                for line in resp.iter_lines()
            ]
        )
        assert "event: log" in text
        assert "event: result" in text
