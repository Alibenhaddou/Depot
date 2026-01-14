import asyncio

import httpx
import pytest
import types

from app.clients.llm import LLMClient
from app.core import config


class BadResponse:
    def __init__(self, status=500, text="bad"):
        self.status_code = status
        self.text = text
        self.request = None

    def json(self):
        return {"choices": [{"message": {"content": "not-json"}}]}


class FakeBadClient:
    def __init__(self, *, timeout=None, headers=None):
        pass

    async def post(self, url, json=None):
        # simulate HTTP error
        raise httpx.HTTPStatusError(
            message="err", request=None, response=BadResponse(status=500, text="server")
        )

    async def aclose(self):
        return None


class FakeInvalidJsonClient:
    def __init__(self, *, timeout=None, headers=None):
        pass

    async def post(self, url, json=None):
        # return success but invalid JSON payload (string that's not JSON)
        return types.SimpleNamespace(
            status_code=200,
            text='{"choices": [{"message": {"content": "not-a-json"}}]}',
            json=lambda: {"choices": [{"message": {"content": "not-a-json"}}]},
        )

    async def aclose(self):
        return None


class FakeRequestErrorClient:
    def __init__(self, *, timeout=None, headers=None):
        pass

    async def post(self, url, json=None):
        raise httpx.RequestError("conn")

    async def aclose(self):
        return None


def test_chat_json_openai_http_error(monkeypatch):
    monkeypatch.setattr(config.settings, "llm_provider", "openai")
    monkeypatch.setattr(config.settings, "openai_api_key", "sk-test")
    monkeypatch.setattr("app.clients.llm.httpx.AsyncClient", FakeBadClient)

    client = LLMClient()
    with pytest.raises(Exception):
        asyncio.run(client.chat_json(system="s", user="u"))


def test_chat_json_openai_invalid_json(monkeypatch):
    monkeypatch.setattr(config.settings, "llm_provider", "openai")
    monkeypatch.setattr(config.settings, "openai_api_key", "sk-test")

    # craft client that returns non-json content
    class FakeClient2:
        def __init__(self, *a, **k):
            pass

        async def post(self, url, json=None):
            return types.SimpleNamespace(
                status_code=200,
                text='{"choices": [{"message": {"content": "not-a-json"}}]}',
                json=lambda: {"choices": [{"message": {"content": "not-a-json"}}]},
            )

        async def aclose(self):
            return None

    monkeypatch.setattr("app.clients.llm.httpx.AsyncClient", FakeClient2)

    client = LLMClient()
    with pytest.raises(Exception):
        asyncio.run(client.chat_json(system="s", user="u"))


def test_chat_json_request_error_ollama(monkeypatch):
    monkeypatch.setattr(config.settings, "llm_provider", "ollama")
    monkeypatch.setattr(config.settings, "llm_base_url", "http://localhost:11434")
    monkeypatch.setattr(config.settings, "llm_model", "m")

    monkeypatch.setattr("app.clients.llm.httpx.AsyncClient", FakeRequestErrorClient)

    client = LLMClient()
    with pytest.raises(Exception):
        asyncio.run(client.chat_text(system="s", user="u"))
