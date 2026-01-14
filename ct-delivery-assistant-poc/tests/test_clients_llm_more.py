import asyncio
import types

import httpx
import pytest

from app.clients.llm import LLMClient
from app.core.config import settings


def test_aclose_calls_client_close(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "llm_base_url", "http://host")
    monkeypatch.setattr(settings, "llm_model", "m")
    monkeypatch.setattr(settings, "llm_timeout", 5)

    closed = {"ok": False}

    class FakeClient:
        async def aclose(self):
            closed["ok"] = True

    c = LLMClient()
    c._client = FakeClient()

    asyncio.run(c.aclose())
    assert closed["ok"]


def test_openai_chat_json_missing_message_content(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "k")
    monkeypatch.setattr(settings, "openai_model", "m")
    monkeypatch.setattr(settings, "llm_timeout", 5)

    c = LLMClient()

    async def fake_post(url, json=None):
        # choices exists but message missing content
        return types.SimpleNamespace(
            status_code=200,
            json=lambda: {"choices": [{"message": {}}]},
            raise_for_status=lambda: None,
        )

    c._client.post = fake_post

    with pytest.raises(Exception) as ei:
        asyncio.run(c.chat_json(system="s", user="u"))
    # Should raise HTTPException or ValueError from json loads mapping
    assert ei


def test_openai_chat_text_content_empty(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "k")
    monkeypatch.setattr(settings, "openai_model", "m")
    monkeypatch.setattr(settings, "llm_timeout", 5)

    c = LLMClient()

    async def fake_post(url, json=None):
        return types.SimpleNamespace(
            status_code=200,
            json=lambda: {"choices": [{"message": {"content": ""}}]},
            raise_for_status=lambda: None,
        )

    c._client.post = fake_post

    with pytest.raises(Exception) as ei:
        asyncio.run(c.chat_text(system="s", user="u"))
    assert ei
