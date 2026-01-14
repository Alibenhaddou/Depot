import json
import os
import redis
from typing import Any, Dict, Optional, cast

from app.core.config import settings

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
)


def _key(sid: str) -> str:
    return f"session:{sid}"


def get_session(sid: str) -> Optional[Dict[str, Any]]:
    key = _key(sid)
    raw = redis_client.get(key)
    if not raw:
        return None
    try:
        session = cast(Dict[str, Any], json.loads(raw))
    except Exception:
        return None

    # refresh TTL
    redis_client.expire(key, settings.session_max_age_seconds)
    return session


def set_session(sid: str, session: Dict[str, Any]) -> None:
    redis_client.set(
        _key(sid),
        json.dumps(session),
        ex=settings.session_max_age_seconds,
    )


def delete_session(sid: str) -> None:
    redis_client.delete(_key(sid))
