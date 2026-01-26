import json
import logging
import os
import redis
from typing import Any, Dict, Optional, cast

from .config import settings

logger = logging.getLogger(__name__)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True,
)

# Fallback in-memory store used when Redis is not available (dev only)
_local_store: Dict[str, str] = {}
_redis_available: Optional[bool] = None
_redis_warned: bool = False


def _mark_redis_unavailable() -> None:
    global _redis_available, _redis_warned
    _redis_available = False
    if not _redis_warned:
        logger.warning("Redis not available, falling back to in-memory sessions")
        _redis_warned = True


def _ensure_redis_available() -> bool:
    global _redis_available
    if _redis_available is False:
        return False
    if _redis_available is True:
        return True
    try:
        redis_client.ping()
        _redis_available = True
        return True
    except Exception:
        _mark_redis_unavailable()
        return False


def _key(sid: str) -> str:
    return f"session:{sid}"


def get_session(sid: str) -> Optional[Dict[str, Any]]:
    """Retrieve a stored session dict from Redis by SID.

    Returns None if the key is missing or contains invalid JSON. On success the
    function refreshes the TTL (sliding session expiration).

    This function is resilient to Redis being unavailable in local/dev
    environments: connection errors are treated as a "missing session" and
    return None rather than bubbling an exception to the caller.
    """
    key = _key(sid)
    if not _ensure_redis_available():
        raw = _local_store.get(key)
    else:
        try:
            raw = redis_client.get(key)
        except Exception:
            # Redis unavailable -> fall back to local store
            _mark_redis_unavailable()
            raw = _local_store.get(key)

    if not raw:
        return None
    try:
        session = cast(Dict[str, Any], json.loads(cast(str, raw)))
    except Exception:
        return None

    # refresh TTL (best-effort; ignore errors)
    if _ensure_redis_available():
        try:
            redis_client.expire(key, settings.session_max_age_seconds)
        except Exception:
            # if redis is down the in-memory store doesn't support TTLs
            _mark_redis_unavailable()
            logger.debug("Redis expire failed (ignored)", exc_info=True)
    return session


def set_session(sid: str, session: Dict[str, Any]) -> None:
    """Store the session in Redis if available.

    Falls back to the in-memory store on errors (dev only).
    """
    key = _key(sid)
    payload = json.dumps(session)
    if not _ensure_redis_available():
        _local_store[key] = payload
        return
    try:
        redis_client.set(key, payload, ex=settings.session_max_age_seconds)
    except Exception:
        _mark_redis_unavailable()
        _local_store[key] = payload


def delete_session(sid: str) -> None:
    if not _ensure_redis_available():
        _local_store.pop(_key(sid), None)
        return
    try:
        redis_client.delete(_key(sid))
    except Exception:
        _mark_redis_unavailable()
        _local_store.pop(_key(sid), None)
