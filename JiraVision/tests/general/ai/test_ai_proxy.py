from fastapi.testclient import TestClient

from app.main import app as main_app
from app.auth.session_store import _sid_serializer
from app.core.redis import set_session

# Monkeypatch helper will replace ai_service.post_json and stream_post


def test_summarize_jql_proxy(monkeypatch):
    # stub post_json to verify payload received and return example
    called = {}

    async def fake_post(path, payload):
        called["path"] = path
        called["payload"] = payload
        return {"result": {"summary": "ok"}}

    monkeypatch.setenv("AI_SERVICE_URL", "http://ai")
    import app.routes.ai as ai_routes

    monkeypatch.setattr(ai_routes, "post_json", fake_post)

    client = TestClient(main_app)

    # create a sid and populate its session directly
    import secrets

    sid = secrets.token_urlsafe(24)
    set_session(
        sid,
        {
            "tokens_by_cloud": {"demo": {"access_token": "x"}},
            "cloud_ids": ["demo"],
            "active_cloud_id": "demo",
        },
    )
    client.cookies.set("sid", _sid_serializer.dumps(sid))

    r2 = client.post(
        "/ai/summarize-jql", json={"jql": "project=PROJ", "max_results": 1}
    )
    assert r2.status_code == 200
    data = r2.json()
    assert data["result"]["summary"] == "ok"
    assert called["path"] == "/ai/summarize-jql"
    # with the current proxy we send jql and max_results
    assert called["payload"]["jql"] == "project=PROJ"


def test_analyze_issue_proxy(monkeypatch):
    async def fake_post(path, payload):
        return {"result": "Analyse distante OK"}

    monkeypatch.setenv("AI_SERVICE_URL", "http://ai")
    import app.routes.ai as ai_routes

    monkeypatch.setattr(ai_routes, "post_json", fake_post)

    client = TestClient(main_app)

    import secrets

    sid = secrets.token_urlsafe(24)
    set_session(
        sid,
        {
            "tokens_by_cloud": {"demo": {"access_token": "x"}},
            "cloud_ids": ["demo"],
            "active_cloud_id": "demo",
        },
    )
    client.cookies.set("sid", _sid_serializer.dumps(sid))

    r2 = client.post("/ai/analyze-issue", json={"issue_key": "PROJ-1"})
    assert r2.status_code == 200
    assert r2.json()["result"] == "Analyse distante OK"


def test_ai_token_endpoint():
    client = TestClient(main_app)

    import secrets

    sid = secrets.token_urlsafe(24)
    set_session(
        sid,
        {
            "tokens_by_cloud": {"demo": {"access_token": "x"}},
            "cloud_ids": ["demo"],
            "active_cloud_id": "demo",
        },
    )
    client.cookies.set("sid", _sid_serializer.dumps(sid))

    r = client.post("/ai/token", json={"cloud_id": "demo"})
    assert r.status_code == 200
    data = r.json()
    assert data["cloud_id"] == "demo"
    assert data["token"]


def test_ai_token_missing_session():
    client = TestClient(main_app)
    r = client.post("/ai/token", json={"cloud_id": "demo"})
    assert r.status_code == 401


def test_analyze_issue_stream_proxy(monkeypatch):
    async def fake_stream(path, payload):
        # simple async generator
        yield 'event: log\ndata: "start"\n\n'
        yield 'event: result\ndata: {"text": "done"}\n\n'

    monkeypatch.setenv("AI_SERVICE_URL", "http://ai")
    import app.routes.ai as ai_routes

    monkeypatch.setattr(ai_routes, "stream_post", fake_stream)

    client = TestClient(main_app)
    import secrets

    sid = secrets.token_urlsafe(24)
    set_session(
        sid,
        {
            "tokens_by_cloud": {"demo": {"access_token": "x"}},
            "cloud_ids": ["demo"],
            "active_cloud_id": "demo",
        },
    )
    client.cookies.set("sid", _sid_serializer.dumps(sid))

    r = client.post("/ai/analyze-issue/stream", json={"issue_key": "PROJ-1"})
    assert r.status_code == 200
    txt = r.text
    assert "event: log" in txt
    assert "event: result" in txt


def test_summarize_jql_proxy_error(monkeypatch):
    import httpx

    async def fake_post(path, payload):
        request = httpx.Request("POST", "http://ai")
        response = httpx.Response(502, request=request)
        raise httpx.HTTPStatusError("boom", request=request, response=response)

    monkeypatch.setenv("AI_SERVICE_URL", "http://ai")
    import app.routes.ai as ai_routes

    monkeypatch.setattr(ai_routes, "post_json", fake_post)

    client = TestClient(main_app)
    r = client.post("/ai/summarize-jql", json={"jql": "project=PROJ", "max_results": 1})
    assert r.status_code == 502


def test_analyze_issue_proxy_404(monkeypatch):
    import httpx

    async def fake_post(path, payload):
        request = httpx.Request("POST", "http://ai")
        response = httpx.Response(404, request=request)
        raise httpx.HTTPStatusError("boom", request=request, response=response)

    monkeypatch.setenv("AI_SERVICE_URL", "http://ai")
    import app.routes.ai as ai_routes

    monkeypatch.setattr(ai_routes, "post_json", fake_post)

    client = TestClient(main_app)
    import secrets

    sid = secrets.token_urlsafe(24)
    set_session(
        sid,
        {
            "tokens_by_cloud": {"demo": {"access_token": "x"}},
            "cloud_ids": ["demo"],
            "active_cloud_id": "demo",
        },
    )
    client.cookies.set("sid", _sid_serializer.dumps(sid))

    r = client.post("/ai/analyze-issue", json={"issue_key": "PROJ-1"})
    assert r.status_code == 404


def test_analyze_issue_proxy_502(monkeypatch):
    import httpx

    async def fake_post(path, payload):
        request = httpx.Request("POST", "http://ai")
        response = httpx.Response(500, request=request)
        raise httpx.HTTPStatusError("boom", request=request, response=response)

    monkeypatch.setenv("AI_SERVICE_URL", "http://ai")
    import app.routes.ai as ai_routes

    monkeypatch.setattr(ai_routes, "post_json", fake_post)

    client = TestClient(main_app)
    import secrets

    sid = secrets.token_urlsafe(24)
    set_session(
        sid,
        {
            "tokens_by_cloud": {"demo": {"access_token": "x"}},
            "cloud_ids": ["demo"],
            "active_cloud_id": "demo",
        },
    )
    client.cookies.set("sid", _sid_serializer.dumps(sid))

    r = client.post("/ai/analyze-issue", json={"issue_key": "PROJ-1"})
    assert r.status_code == 502


def test_analyze_issue_stream_proxy_error(monkeypatch):
    async def fake_stream(path, payload):
        if False:
            yield ""
        raise Exception("boom")

    monkeypatch.setenv("AI_SERVICE_URL", "http://ai")
    import app.routes.ai as ai_routes

    monkeypatch.setattr(ai_routes, "stream_post", fake_stream)

    client = TestClient(main_app)
    import secrets

    sid = secrets.token_urlsafe(24)
    set_session(
        sid,
        {
            "tokens_by_cloud": {"demo": {"access_token": "x"}},
            "cloud_ids": ["demo"],
            "active_cloud_id": "demo",
        },
    )
    client.cookies.set("sid", _sid_serializer.dumps(sid))

    r = client.post("/ai/analyze-issue/stream", json={"issue_key": "PROJ-1"})
    assert r.status_code == 200
    assert "Erreur ai-service (stream)" in r.text
