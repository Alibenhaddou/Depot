from __future__ import annotations

import json
import logging
from typing import Any, Dict

import httpx
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    def __init__(self) -> None:
        if settings.llm_provider != "ollama":
            raise RuntimeError(f"LLM_PROVIDER non supporté: {settings.llm_provider}")

        self.base_url = (settings.llm_base_url or "").rstrip("/")
        self.model = settings.llm_model
        self.timeout = settings.llm_timeout

        if self.base_url.endswith("/api"):
            self.api_base = self.base_url[: -len("/api")]
        else:
            self.api_base = self.base_url

        self._client = httpx.AsyncClient(timeout=self.timeout)

        logger.debug("[LLM] provider=ollama model=%s api_base=%s", self.model, self.api_base)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def chat_json(self, *, system: str, user: str) -> Dict[str, Any]:
        url = f"{self.api_base}/api/chat"
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {"temperature": 0.2, "num_predict": 256, "num_ctx": 2048},
        }

        logger.debug("[LLM] POST %s", url)

        try:
            r = await self._client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPStatusError as e:
            logger.warning("[LLM] HTTP %s on %s: %s", e.response.status_code, e.request.url, (e.response.text or "")[:300])
            raise HTTPException(status_code=502, detail="LLM error (HTTP)")
        except httpx.RequestError as e:
            logger.warning("[LLM] unreachable %s: %s", url, e)
            raise HTTPException(status_code=502, detail="LLM unreachable")

        content = (data.get("message") or {}).get("content") or ""
        try:
            return json.loads(content)
        except Exception:
            logger.warning("[LLM] invalid JSON returned (len=%d)", len(content))
            raise HTTPException(status_code=502, detail="LLM returned invalid JSON")

    async def chat_text(self, *, system: str, user: str) -> str:
        url = f"{self.api_base}/api/chat"
        payload = {
            "model": self.model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "options": {"temperature": 0.2, "num_predict": 256, "num_ctx": 2048},
        }

        logger.debug("[LLM] POST %s", url)

        try:
            r = await self._client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
        except httpx.HTTPStatusError as e:
            logger.warning("[LLM] HTTP %s on %s: %s", e.response.status_code, e.request.url, (e.response.text or "")[:300])
            raise HTTPException(status_code=502, detail="LLM error (HTTP)")
        except httpx.RequestError as e:
            logger.warning("[LLM] unreachable %s: %s", url, e)
            raise HTTPException(status_code=502, detail="LLM unreachable")

        content = (data.get("message") or {}).get("content") or ""
        if not content:
            raise HTTPException(status_code=502, detail="LLM returned empty response")
        return content
