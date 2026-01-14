from __future__ import annotations

import json
import logging
from typing import Any, Dict

import httpx
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


def _log_http_status(e: httpx.HTTPStatusError) -> None:
    """Log a compact summary for an httpx.HTTPStatusError.

    This avoids dumping large response bodies into logs while preserving
    the important fields (status code, request URL and a short snippet).
    """
    status = e.response.status_code
    req_url = e.request.url
    snippet = (e.response.text or "")[:300]
    logger.warning("[LLM] HTTP %s on %s: %s", status, req_url, snippet)


class LLMClient:
    def __init__(self) -> None:
        provider = (settings.llm_provider or "").strip().lower()
        self.timeout = settings.llm_timeout

        if provider == "ollama":
            self.base_url = (settings.llm_base_url or "").rstrip("/")
            self.model = settings.llm_model

            if self.base_url.endswith("/api"):
                self.api_base = self.base_url[: -len("/api")]
            else:
                self.api_base = self.base_url

            self._client = httpx.AsyncClient(timeout=self.timeout)
            self._provider = "ollama"

            logger.debug(
                "[LLM] provider=ollama model=%s api_base=%s",
                self.model,
                self.api_base,
            )

        elif provider == "openai":
            if not settings.openai_api_key:
                raise RuntimeError("OPENAI_API_KEY required when LLM_PROVIDER=openai")
            self.base_url = "https://api.openai.com/v1"
            self.model = settings.openai_model
            headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
            self._client = httpx.AsyncClient(timeout=self.timeout, headers=headers)
            self._provider = "openai"

            logger.debug(
                "[LLM] provider=openai model=%s api_base=%s",
                self.model,
                self.base_url,
            )

        else:
            raise RuntimeError(f"LLM_PROVIDER non supporté: {settings.llm_provider}")

    async def aclose(self) -> None:
        await self._client.aclose()

    async def chat_json(self, *, system: str, user: str) -> Any:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        if self._provider == "ollama":
            url = f"{self.api_base}/api/chat"
            payload = {
                "model": self.model,
                "stream": False,
                "format": "json",
                "messages": messages,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 256,
                    "num_ctx": 2048,
                },
            }

            logger.debug("[LLM] POST %s", url)

            try:
                r = await self._client.post(url, json=payload)
                r.raise_for_status()
                data = r.json()
            except httpx.HTTPStatusError as e:
                _log_http_status(e)
                raise HTTPException(
                    status_code=502,
                    detail="LLM error (HTTP)",
                )
            except httpx.RequestError as e:
                logger.warning("[LLM] unreachable %s: %s", url, e)
                raise HTTPException(
                    status_code=502,
                    detail="LLM unreachable",
                )

            content = (data.get("message") or {}).get("content") or ""
            try:
                return json.loads(content)
            except Exception:
                logger.warning("[LLM] invalid JSON returned (len=%d)", len(content))
                raise HTTPException(status_code=502, detail="LLM returned invalid JSON")

        else:  # openai
            url = f"{self.base_url}/chat/completions"
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 2048,
            }

            logger.debug("[LLM] POST %s", url)

            try:
                r = await self._client.post(url, json=payload)
                r.raise_for_status()
                data = r.json()
            except httpx.HTTPStatusError as e:
                _log_http_status(e)
                raise HTTPException(status_code=502, detail="LLM error (HTTP)")
            except httpx.RequestError as e:
                logger.warning("[LLM] unreachable %s: %s", url, e)
                raise HTTPException(status_code=502, detail="LLM unreachable")

            # OpenAI returns choices -> message -> content
            choices = data.get("choices") or []
            if not choices:
                raise HTTPException(
                    status_code=502,
                    detail="LLM returned empty response",
                )
            content = (choices[0].get("message") or {}).get("content") or ""
            try:
                return json.loads(content)
            except Exception:
                logger.warning("[LLM] invalid JSON returned (len=%d)", len(content))
                raise HTTPException(
                    status_code=502,
                    detail="LLM returned invalid JSON",
                )

    async def chat_text(self, *, system: str, user: str) -> str:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

        if self._provider == "ollama":
            url = f"{self.api_base}/api/chat"
            payload = {
                "model": self.model,
                "stream": False,
                "messages": messages,
                "options": {
                    "temperature": 0.2,
                    "num_predict": 256,
                    "num_ctx": 2048,
                },
            }

            logger.debug("[LLM] POST %s", url)

            try:
                r = await self._client.post(url, json=payload)
                r.raise_for_status()
                data = r.json()
            except httpx.HTTPStatusError as e:
                _log_http_status(e)
                raise HTTPException(
                    status_code=502,
                    detail="LLM error (HTTP)",
                )
            except httpx.RequestError as e:
                logger.warning("[LLM] unreachable %s: %s", url, e)
                raise HTTPException(
                    status_code=502,
                    detail="LLM unreachable",
                )

            content = (data.get("message") or {}).get("content") or ""
            if not content:
                raise HTTPException(
                    status_code=502,
                    detail="LLM returned empty response",
                )
            return content

        else:  # openai
            url = f"{self.base_url}/chat/completions"
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.2,
                "max_tokens": 2048,
            }

            logger.debug("[LLM] POST %s", url)

            try:
                r = await self._client.post(url, json=payload)
                r.raise_for_status()
                data = r.json()
            except httpx.HTTPStatusError as e:
                _log_http_status(e)
                raise HTTPException(status_code=502, detail="LLM error (HTTP)")
            except httpx.RequestError as e:
                logger.warning("[LLM] unreachable %s: %s", url, e)
                raise HTTPException(status_code=502, detail="LLM unreachable")

            choices = data.get("choices") or []
            if not choices:
                raise HTTPException(
                    status_code=502,
                    detail="LLM returned empty response",
                )
            content = (choices[0].get("message") or {}).get("content") or ""
            if not content:
                raise HTTPException(
                    status_code=502,
                    detail="LLM returned empty response",
                )
            return content
