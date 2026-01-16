import os
from typing import Any, AsyncIterator, Dict

import httpx

from app.core.config import settings
from app.core.ai_token import generate_ai_token


def _ai_url() -> str:
    # Allow runtime override via env for canary/prod without code changes.
    return os.getenv("AI_SERVICE_URL") or (settings.ai_service_url or "")


def _auth_headers(payload: Dict[str, Any]) -> Dict[str, str]:
    # Inter-service auth is optional; token is short-lived and signed.
    if not settings.ai_auth_enabled:
        return {}
    token = generate_ai_token({"cloud_id": payload.get("cloud_id")})
    return {"Authorization": f"Bearer {token}"}


async def post_json(path: str, payload: Dict[str, Any]) -> Any:
    ai_url = _ai_url()
    if not ai_url:
        raise RuntimeError("AI_SERVICE_URL not configured")
    url = f"{ai_url.rstrip('/')}{path}"
    headers = _auth_headers(payload)
    async with httpx.AsyncClient(timeout=60) as client:
        r = await client.post(url, json=payload, headers=headers)
        r.raise_for_status()
        return r.json()


async def stream_post(path: str, payload: Dict[str, Any]) -> AsyncIterator[str]:
    ai_url = _ai_url()
    if not ai_url:
        raise RuntimeError("AI_SERVICE_URL not configured")
    url = f"{ai_url.rstrip('/')}{path}"
    headers = _auth_headers(payload)
    async with httpx.AsyncClient(timeout=600) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            async for chunk in resp.aiter_text():
                yield chunk
