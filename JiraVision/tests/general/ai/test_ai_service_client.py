import httpx
import pytest

from app.clients import ai_service as ai_service_client
from app.core import config as app_config


class DummyResponse:
    def __init__(self, json_data=None, status_code=200):
        self._json = json_data or {"ok": True}
        self.status_code = status_code
        self.request = httpx.Request("POST", "http://ai")
        self.text = ""

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )

    def json(self):
        return self._json


class DummyStream:
    def __init__(self, chunks, status_code=200):
        self._chunks = chunks
        self.status_code = status_code
        self.request = httpx.Request("POST", "http://ai")

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "error",
                request=self.request,
                response=httpx.Response(self.status_code, request=self.request),
            )

    async def aiter_text(self):
        for chunk in self._chunks:
            yield chunk


class DummyAsyncClient:
    def __init__(self, timeout=None):
        self.timeout = timeout
        self.last_headers = None
        self.last_url = None
        self.last_json = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None, headers=None):
        self.last_url = url
        self.last_json = json
        self.last_headers = headers
        return DummyResponse({"ok": True})

    def stream(self, method, url, json=None, headers=None):
        self.last_url = url
        self.last_json = json
        self.last_headers = headers
        return DummyStream(["a", "b"])


@pytest.mark.asyncio
async def test_post_json_with_auth(monkeypatch):
    monkeypatch.setenv("AI_SERVICE_URL", "http://ai")
    monkeypatch.setattr(ai_service_client.httpx, "AsyncClient", DummyAsyncClient)

    monkeypatch.setattr(app_config.settings, "ai_auth_enabled", True)
    monkeypatch.setattr(app_config.settings, "ai_shared_secret", "secret")

    result = await ai_service_client.post_json("/ai/summarize-jql", {"cloud_id": "demo"})
    assert result["ok"] is True


@pytest.mark.asyncio
async def test_stream_post_yields(monkeypatch):
    monkeypatch.setenv("AI_SERVICE_URL", "http://ai")
    monkeypatch.setattr(ai_service_client.httpx, "AsyncClient", DummyAsyncClient)

    chunks = []
    async for chunk in ai_service_client.stream_post("/ai/analyze-issue/stream", {"cloud_id": "demo"}):
        chunks.append(chunk)

    assert chunks == ["a", "b"]


@pytest.mark.asyncio
async def test_post_json_missing_url_raises(monkeypatch):
    monkeypatch.delenv("AI_SERVICE_URL", raising=False)
    monkeypatch.setattr(app_config.settings, "ai_service_url", None)
    with pytest.raises(RuntimeError):
        await ai_service_client.post_json("/ai/summarize-jql", {"cloud_id": "demo"})


@pytest.mark.asyncio
async def test_stream_post_missing_url_raises(monkeypatch):
    monkeypatch.delenv("AI_SERVICE_URL", raising=False)
    monkeypatch.setattr(app_config.settings, "ai_service_url", None)
    with pytest.raises(RuntimeError):
        async for _ in ai_service_client.stream_post("/ai/analyze-issue/stream", {"cloud_id": "demo"}):
            pass
