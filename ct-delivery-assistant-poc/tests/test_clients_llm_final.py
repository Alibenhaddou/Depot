import asyncio

import httpx
import pytest

from fastapi import HTTPException

from app.clients.llm import LLMClient
from app.core.config import settings


def test_unsupported_provider_raises(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "bananas")
    with pytest.raises(RuntimeError):
        LLMClient()


def test_openai_chat_json_httpstatus(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "k")
    monkeypatch.setattr(settings, "openai_model", "m")
    monkeypatch.setattr(settings, "llm_timeout", 5)

    c = LLMClient()

    async def fake_post(url, json=None):
        req = httpx.Request("POST", "http://x")
        resp = httpx.Response(500, request=req, content=b"err")
        raise httpx.HTTPStatusError("err", request=req, response=resp)

    c._client.post = fake_post

    with pytest.raises(HTTPException) as ei:
        asyncio.run(c.chat_json(system="s", user="u"))
    assert ei.value.status_code == 502


def test_openai_chat_text_http_and_request_errors(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openai")
    monkeypatch.setattr(settings, "openai_api_key", "k")
    monkeypatch.setattr(settings, "openai_model", "m")
    monkeypatch.setattr(settings, "llm_timeout", 5)

    c = LLMClient()

    async def fake_post_http(url, json=None):
        req = httpx.Request("POST", "http://x")
        resp = httpx.Response(500, request=req, content=b"err")
        raise httpx.HTTPStatusError("err", request=req, response=resp)

    c._client.post = fake_post_http
    with pytest.raises(HTTPException) as ei:
        asyncio.run(c.chat_text(system="s", user="u"))
    assert ei.value.status_code == 502

    async def fake_post_req(url, json=None):
        raise httpx.RequestError("conn")

    c._client.post = fake_post_req
    with pytest.raises(HTTPException) as ei2:
        asyncio.run(c.chat_text(system="s", user="u"))
    assert ei2.value.status_code == 502


def test_ollama_chat_text_http_error(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "ollama")
    monkeypatch.setattr(settings, "llm_base_url", "http://host")
    monkeypatch.setattr(settings, "llm_model", "m")
    monkeypatch.setattr(settings, "llm_timeout", 5)

    c = LLMClient()

    async def fake_post(url, json=None):
        req = httpx.Request("POST", "http://x")
        resp = httpx.Response(502, request=req, content=b"err")
        raise httpx.HTTPStatusError("err", request=req, response=resp)

    c._client.post = fake_post

    with pytest.raises(HTTPException) as ei:
        asyncio.run(c.chat_text(system="s", user="u"))
    assert ei.value.status_code == 502
