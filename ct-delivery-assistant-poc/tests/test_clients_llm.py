import json
import types

import pytest

from app.clients.llm import LLMClient
from app.core import config


class FakeResponse:
    def __init__(self, data):
        self._data = data
        self.text = json.dumps(data)
        self.status_code = 200

    def json(self):
        return self._data

    def raise_for_status(self):
        return None


class FakeAsyncClient:
    def __init__(self, *, timeout=None, headers=None):
        self._timeout = timeout
        self._headers = headers
        self._posted = []

    async def post(self, url, json=None):
        self._posted.append((url, json))
        # Return a response shaped like Ollama
        if "/api/chat" in url:
            return FakeResponse({"message": {"content": json.get("messages") and "{\"ok\": true}"}})
        # OpenAI style
        return FakeResponse({"choices": [{"message": {"content": '{"ok": true}'}}]})

    async def aclose(self):
        return None

import asyncio

def test_chat_json_openai(monkeypatch):
    # configure settings for openai
    monkeypatch.setattr(config.settings, "llm_provider", "openai")
    monkeypatch.setattr(config.settings, "openai_api_key", "sk-abc")
    monkeypatch.setattr(config.settings, "openai_model", "gpt-test")

    # patch AsyncClient used inside LLMClient
    monkeypatch.setattr("app.clients.llm.httpx.AsyncClient", FakeAsyncClient)

    client = LLMClient()
    data = asyncio.run(client.chat_json(system="s", user="u"))
    assert data == {"ok": True}


def test_chat_text_ollama(monkeypatch):
    monkeypatch.setattr(config.settings, "llm_provider", "ollama")
    monkeypatch.setattr(config.settings, "llm_base_url", "http://localhost:11434")
    monkeypatch.setattr(config.settings, "llm_model", "m")

    monkeypatch.setattr("app.clients.llm.httpx.AsyncClient", FakeAsyncClient)

    client = LLMClient()
    text = asyncio.run(client.chat_text(system="s", user="u"))
    assert "{\"ok\": true}" in text
