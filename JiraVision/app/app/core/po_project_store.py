import json
import logging
import time
from typing import Any, Dict, List, Optional

from app.core.redis import redis_client

logger = logging.getLogger(__name__)

_VALID_SOURCES = {"jira", "manual"}
_VALID_MASK_TYPES = {"none", "temporaire", "definitif"}

_local_store: Dict[str, str] = {}


def _now_ts() -> int:
    return int(time.time())


def _user_key(jira_account_id: str) -> str:
    return f"po_user:{jira_account_id}"


def _projects_key(jira_account_id: str) -> str:
    return f"po_projects:{jira_account_id}"


def _project_id(project_key: str, cloud_id: Optional[str]) -> str:
    return f"{cloud_id or 'default'}:{project_key}"


def _get_raw(key: str) -> Optional[str]:
    try:
        return redis_client.get(key)
    except Exception:
        logger.warning("Redis not available, falling back to in-memory store")
        return _local_store.get(key)


def _set_raw(key: str, payload: str) -> None:
    try:
        redis_client.set(key, payload)
    except Exception:
        logger.warning("Redis write failed, using in-memory store")
        _local_store[key] = payload


def _load_json(key: str) -> Optional[Dict[str, Any]]:
    raw = _get_raw(key)
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except Exception:
        return None
    if not isinstance(data, dict):
        return None
    return data


def _save_json(key: str, data: Dict[str, Any]) -> None:
    payload = json.dumps(data)
    _set_raw(key, payload)


def get_user(jira_account_id: str) -> Optional[Dict[str, Any]]:
    return _load_json(_user_key(jira_account_id))


def upsert_user(
    jira_account_id: str,
    *,
    display_name: Optional[str] = None,
    email: Optional[str] = None,
    now: Optional[int] = None,
) -> Dict[str, Any]:
    now_ts = now or _now_ts()
    user = get_user(jira_account_id) or {
        "jira_account_id": jira_account_id,
        "created_at": now_ts,
    }

    if display_name is not None:
        user["display_name"] = display_name
    if email is not None:
        user["email"] = email

    user["updated_at"] = now_ts
    _save_json(_user_key(jira_account_id), user)
    return user


def set_last_synced_at(
    jira_account_id: str,
    *,
    ts: Optional[int] = None,
) -> Dict[str, Any]:
    now_ts = ts or _now_ts()
    user = get_user(jira_account_id) or {
        "jira_account_id": jira_account_id,
        "created_at": now_ts,
    }
    user["last_synced_at"] = now_ts
    user["updated_at"] = now_ts
    _save_json(_user_key(jira_account_id), user)
    return user


def _load_projects(jira_account_id: str) -> Dict[str, Dict[str, Any]]:
    return _load_json(_projects_key(jira_account_id)) or {}


def list_projects_for_user(jira_account_id: str) -> List[Dict[str, Any]]:
    projects = _load_projects(jira_account_id)
    return sorted(
        projects.values(),
        key=lambda p: (p.get("project_key") or "", p.get("cloud_id") or ""),
    )


def upsert_project_for_user(
    jira_account_id: str,
    *,
    project_key: str,
    project_name: str,
    source: str,
    cloud_id: Optional[str] = None,
    mask_type: str = "none",
    masked_at: Optional[int] = None,
    now: Optional[int] = None,
) -> Dict[str, Any]:
    if source not in _VALID_SOURCES:
        raise ValueError(f"Invalid source: {source}")
    if mask_type not in _VALID_MASK_TYPES:
        raise ValueError(f"Invalid mask_type: {mask_type}")

    now_ts = now or _now_ts()
    projects = _load_projects(jira_account_id)
    pid = _project_id(project_key, cloud_id)
    project = projects.get(pid) or {
        "project_key": project_key,
        "cloud_id": cloud_id,
        "created_at": now_ts,
    }

    project["project_name"] = project_name
    project["source"] = source
    project["updated_at"] = now_ts

    if mask_type == "none":
        project["mask_type"] = "none"
        project["masked_at"] = None
    else:
        project["mask_type"] = mask_type
        project["masked_at"] = masked_at if masked_at is not None else now_ts

    projects[pid] = project
    _save_json(_projects_key(jira_account_id), projects)
    return project


def set_project_mask(
    jira_account_id: str,
    *,
    project_key: str,
    cloud_id: Optional[str],
    mask_type: str,
    now: Optional[int] = None,
) -> Dict[str, Any]:
    if mask_type not in _VALID_MASK_TYPES:
        raise ValueError(f"Invalid mask_type: {mask_type}")

    projects = _load_projects(jira_account_id)
    pid = _project_id(project_key, cloud_id)
    if pid not in projects:
        raise KeyError(f"Project not found: {pid}")

    now_ts = now or _now_ts()
    project = projects[pid]
    if mask_type == "none":
        project["mask_type"] = "none"
        project["masked_at"] = None
    else:
        project["mask_type"] = mask_type
        project["masked_at"] = now_ts

    project["updated_at"] = now_ts
    projects[pid] = project
    _save_json(_projects_key(jira_account_id), projects)
    return project
