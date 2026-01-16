import pytest

from app.core import po_project_store as store
from app.core.po_user import upsert_user_from_jira


def _force_local_store(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise RuntimeError("redis down")

    monkeypatch.setattr(store.redis_client, "get", _boom)
    monkeypatch.setattr(store.redis_client, "set", _boom)
    store._local_store.clear()


def test_upsert_user_from_jira_creates(monkeypatch):
    _force_local_store(monkeypatch)

    me = {"accountId": "acct", "displayName": "Alice", "emailAddress": "a@b.com"}
    user = upsert_user_from_jira(me, now=100)

    assert user["jira_account_id"] == "acct"
    assert user["display_name"] == "Alice"
    assert user["email"] == "a@b.com"
    assert user["created_at"] == 100


def test_upsert_user_from_jira_missing_email(monkeypatch):
    _force_local_store(monkeypatch)

    me = {"accountId": "acct", "displayName": "Alice"}
    user = upsert_user_from_jira(me, now=200)

    assert user["jira_account_id"] == "acct"
    assert user["display_name"] == "Alice"
    assert user.get("email") is None


def test_upsert_user_from_jira_missing_account_id(monkeypatch):
    _force_local_store(monkeypatch)

    with pytest.raises(ValueError):
        upsert_user_from_jira({"displayName": "Alice"})
