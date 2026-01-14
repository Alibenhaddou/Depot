import asyncio
import json
import types

import httpx
import pytest

from fastapi import HTTPException

from app.clients.llm import LLMClient, _log_http_status
from app.core.config import settings


def test_ollama_api_base_trim(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "llm_base_url", "http://host/api")
    monkeypatch.setattr(settings, "llm_model", "m")
    monkeypatch.setattr(settings, "llm_timeout", 5)

    c = LLMClient()
    assert c._provider == "ollama"
    assert c.api_base == "http://host"


def test_openai_missing_key(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "openai_model", "m")
    monkeypatch.setattr(settings, "llm_timeout", 5)

    with pytest.raises(RuntimeError):
        LLMClient()


def _make_resp(json_data=None, text="", status=200):
    class R:
        def __init__(self, json_data, text, status):
            self._j = json_data
            self.text = text
            self.status_code = status
            self.request = types.SimpleNamespace(url="http://test")

        def json(self):
            return self._j

        def raise_for_status(self):
            if self.status_code >= 400:
                req = httpx.Request("POST", "http://test")
                resp = httpx.Response(
                    self.status_code, request=req, content=(self.text or "").encode()
                )
                raise httpx.HTTPStatusError("err", request=req, response=resp)

    return R(json_data, text, status)


def test__log_http_status_logs(caplog):
    req = httpx.Request("GET", "http://x")
    resp = httpx.Response(502, request=req, content=b"abcd")
    err = httpx.HTTPStatusError("x", request=req, response=resp)
    caplog.set_level("WARNING")
    _log_http_status(err)
    assert "HTTP" in caplog.text


def test_chat_json_ollama_success(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "llm_base_url", "http://host")
    monkeypatch.setattr(settings, "llm_model", "m")
    monkeypatch.setattr(settings, "llm_timeout", 5)

    c = LLMClient()

    async def fake_post(url, json=None):
        return _make_resp({"message": {"content": '{"k": 1}'}}, "", 200)

    c._client.post = fake_post

    res = asyncio.run(c.chat_json(system="s", user="u"))
    assert res == {"k": 1}


def test_chat_json_ollama_invalid_json(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "llm_base_url", "http://host")
    monkeypatch.setattr(settings, "llm_model", "m")
    monkeypatch.setattr(settings, "llm_timeout", 5)

    c = LLMClient()

    async def fake_post(url, json=None):
        return _make_resp({"message": {"content": "not-json"}}, "not-json", 200)

    c._client.post = fake_post

    with pytest.raises(HTTPException) as ei:
        asyncio.run(c.chat_json(system="s", user="u"))
    assert ei.value.status_code == 502


def test_chat_json_ollama_http_error(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "llm_base_url", "http://host")
    monkeypatch.setattr(settings, "llm_model", "m")
    monkeypatch.setattr(settings, "llm_timeout", 5)

    c = LLMClient()

    async def fake_post(url, json=None):
        req = httpx.Request("POST", "http://test")
        resp = httpx.Response(502, request=req, content=b"err")
        raise httpx.HTTPStatusError("err", request=req, response=resp)

    c._client.post = fake_post

    with pytest.raises(HTTPException) as ei:
        asyncio.run(c.chat_json(system="s", user="u"))
    assert ei.value.status_code == 502


def test_chat_json_ollama_request_error(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "llm_base_url", "http://host")
    monkeypatch.setattr(settings, "llm_model", "m")
    monkeypatch.setattr(settings, "llm_timeout", 5)

    c = LLMClient()

    async def fake_post(url, json=None):
        raise httpx.RequestError("conn")

    c._client.post = fake_post

    with pytest.raises(HTTPException) as ei:
        asyncio.run(c.chat_json(system="s", user="u"))
    assert ei.value.status_code == 502


def test_chat_json_openai_empty_choices(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "k")
    monkeypatch.setattr(settings, "openai_model", "m")
    monkeypatch.setattr(settings, "llm_timeout", 5)

    c = LLMClient()

    async def fake_post(url, json=None):
        return _make_resp({"choices": []}, "", 200)

    c._client.post = fake_post

    with pytest.raises(HTTPException) as ei:
        asyncio.run(c.chat_json(system="s", user="u"))
    assert ei.value.status_code == 502


def test_chat_text_ollama_empty_response(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "llm_base_url", "http://host")
    monkeypatch.setattr(settings, "llm_model", "m")
    monkeypatch.setattr(settings, "llm_timeout", 5)

    c = LLMClient()

    async def fake_post(url, json=None):
        return _make_resp({"message": {"content": ""}}, "", 200)

    c._client.post = fake_post

    with pytest.raises(HTTPException) as ei:
        asyncio.run(c.chat_text(system="s", user="u"))
    assert ei.value.status_code == 502


def test_openai_chat_json_success(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "k")
    monkeypatch.setattr(settings, "openai_model", "m")
    monkeypatch.setattr(settings, "llm_timeout", 5)

    c = LLMClient()

    async def fake_post(url, json=None):
        return _make_resp({"choices": [{"message": {"content": '{"a": 1}'}}]}, "", 200)

    c._client.post = fake_post

    res = asyncio.run(c.chat_json(system="s", user="u"))
    assert res == {"a": 1}


def test_openai_chat_json_invalid_json(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "k")
    monkeypatch.setattr(settings, "openai_model", "m")
    monkeypatch.setattr(settings, "llm_timeout", 5)

    c = LLMClient()

    async def fake_post(url, json=None):
        return _make_resp(
            {"choices": [{"message": {"content": "not-json"}}]}, "not-json", 200
        )

    c._client.post = fake_post

    with pytest.raises(HTTPException) as ei:
        asyncio.run(c.chat_json(system="s", user="u"))
    assert ei.value.status_code == 502


def test_openai_chat_text_empty_choice(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "k")
    monkeypatch.setattr(settings, "openai_model", "m")
    monkeypatch.setattr(settings, "llm_timeout", 5)

    c = LLMClient()

    async def fake_post(url, json=None):
        return _make_resp({"choices": []}, "", 200)

    c._client.post = fake_post

    with pytest.raises(HTTPException) as ei:
        asyncio.run(c.chat_text(system="s", user="u"))
    assert ei.value.status_code == 502


def test_openai_request_error(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "k")
    monkeypatch.setattr(settings, "openai_model", "m")
    monkeypatch.setattr(settings, "llm_timeout", 5)

    c = LLMClient()

    async def fake_post(url, json=None):
        raise httpx.RequestError("conn")

    c._client.post = fake_post

    with pytest.raises(HTTPException) as ei:
        asyncio.run(c.chat_json(system="s", user="u"))
    assert ei.value.status_code == 502
