import pathlib
import sys

root = pathlib.Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from fastapi.testclient import TestClient  # noqa: E402

import ai_app.clients.llm as ai_llm  # noqa: E402
import ai_app.core.auth as ai_auth  # noqa: E402
import ai_app.core.telemetry as ai_telemetry  # noqa: E402
import ai_app.main as ai_main  # noqa: E402
import ai_app.routes.ai as ai_routes  # noqa: E402

client = TestClient(ai_main.app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.text == "ok"


def test_ready():
    r = client.get("/ready")
    assert r.status_code == 200
    assert r.text == "ready"


def test_metrics_endpoint():
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "text/plain" in r.headers.get("content-type", "")


def test_summarize_jql(monkeypatch):
    async def fake_chat_json(*, system: str, user: str):
        return {
            "summary": "Résumé test",
            "highlights": [],
            "risks": [],
            "next_actions": [],
        }

    monkeypatch.setattr(ai_routes.llm, "chat_json", fake_chat_json)

    r = client.post(
        "/ai/summarize-jql",
        json={
            "jql": "project=PROJ",
            "max_results": 1,
            "issues": [{"key": "PROJ-1", "summary": "Test", "status": "Open"}],
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert "cloud_id" in data
    assert data["count"] == 1
    assert data["result"]["summary"] == "Résumé test"


def test_analyze_issue():
    r = client.post("/ai/analyze-issue", json={"issue_key": "PROJ-1"})
    assert r.status_code == 200
    data = r.json()
    assert data["result"] == "Analyse exemple"


def test_analyze_issue_stream_returns_sse():
    with client.stream(
        "POST", "/ai/analyze-issue/stream", json={"issue_key": "PROJ-1"}
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


def test_ai_auth_disabled_accepts_without_header(monkeypatch):
    # By default ai_auth_enabled is False in settings, so verify_ai_token should accept.
    monkeypatch.setattr(ai_auth.settings, "ai_auth_enabled", False)
    assert ai_auth.verify_ai_token(None) == {}


def test_ai_auth_enabled_missing_header_401(monkeypatch):
    monkeypatch.setattr(ai_auth.settings, "ai_auth_enabled", True)
    try:
        ai_auth.verify_ai_token(None)
        assert False, "expected HTTPException"
    except Exception as e:
        # fastapi.HTTPException
        assert getattr(e, "status_code", None) == 401


def test_ai_auth_enabled_invalid_token_401(monkeypatch):
    monkeypatch.setattr(ai_auth.settings, "ai_auth_enabled", True)
    try:
        ai_auth.verify_ai_token("Bearer invalid")
        assert False, "expected HTTPException"
    except Exception as e:
        assert getattr(e, "status_code", None) == 401


def test_telemetry_no_endpoint(monkeypatch):
    # When OTEL_EXPORTER_OTLP_ENDPOINT is absent, setup_telemetry is a no-op.
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    app = ai_main.FastAPI()
    ai_telemetry.setup_telemetry(app, "svc")


def test_telemetry_import_error(monkeypatch):
    # Sonar: http insecure -> utiliser https même en tests.
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://otel")
    real_import = __import__

    def fake_import(name, *args, **kwargs):
        if name.startswith("opentelemetry"):
            raise ImportError("boom")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    app = ai_main.FastAPI()
    ai_telemetry.setup_telemetry(app, "svc")


def test_llm_client_unsupported_provider_raises(monkeypatch):
    monkeypatch.setattr(ai_llm.settings, "llm_provider", "unknown")
    try:
        ai_llm.LLMClient()
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass


def test_llm_client_openai_missing_key_raises(monkeypatch):
    monkeypatch.setattr(ai_llm.settings, "llm_provider", "openai")
    monkeypatch.setattr(ai_llm.settings, "openai_api_key", None)
    try:
        ai_llm.LLMClient()
        assert False, "expected RuntimeError"
    except RuntimeError:
        pass


def test_llm_chat_json_ollama_invalid_json_maps_502(monkeypatch):
    # Force provider=ollama
    monkeypatch.setattr(ai_llm.settings, "llm_provider", "ollama")
    # Sonar: http insecure -> utiliser https même en tests.
    monkeypatch.setattr(ai_llm.settings, "llm_base_url", "https://ollama:11434")
    monkeypatch.setattr(ai_llm.settings, "llm_model", "m")

    client = ai_llm.LLMClient()

    class DummyResp:
        def __init__(self):
            self.text = "{bad"

        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": "{bad"}}

    async def fake_post(url, json=None):
        return DummyResp()

    monkeypatch.setattr(client._client, "post", fake_post)

    try:
        import asyncio

        asyncio.get_event_loop().run_until_complete(
            client.chat_json(system="s", user="u")
        )
        assert False, "expected HTTPException"
    except Exception as e:
        assert getattr(e, "status_code", None) == 502


def test_llm_chat_text_ollama_empty_response_maps_502(monkeypatch):
    monkeypatch.setattr(ai_llm.settings, "llm_provider", "ollama")
    # Sonar: http insecure -> utiliser https même en tests.
    monkeypatch.setattr(ai_llm.settings, "llm_base_url", "https://ollama:11434")
    monkeypatch.setattr(ai_llm.settings, "llm_model", "m")

    client = ai_llm.LLMClient()

    class DummyResp:
        def __init__(self):
            self.text = ""

        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": ""}}

    async def fake_post(url, json=None):
        return DummyResp()

    monkeypatch.setattr(client._client, "post", fake_post)

    try:
        import asyncio

        asyncio.get_event_loop().run_until_complete(
            client.chat_text(system="s", user="u")
        )
        assert False, "expected HTTPException"
    except Exception as e:
        assert getattr(e, "status_code", None) == 502
