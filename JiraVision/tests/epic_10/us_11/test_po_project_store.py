import pytest

from app.core import po_project_store as store


def _force_local_store(monkeypatch):
    def _boom(*_args, **_kwargs):
        raise RuntimeError("redis down")

    monkeypatch.setattr(store.redis_client, "get", _boom)
    monkeypatch.setattr(store.redis_client, "set", _boom)
    store._local_store.clear()


def test_upsert_user_create_and_update(monkeypatch):
    _force_local_store(monkeypatch)

    user = store.upsert_user("acct", display_name="Alice", email="a@b.com", now=100)
    assert user["jira_account_id"] == "acct"
    assert user["created_at"] == 100
    assert user["updated_at"] == 100
    assert user["display_name"] == "Alice"
    assert user["email"] == "a@b.com"

    user2 = store.upsert_user("acct", display_name="Alicia", now=200)
    assert user2["created_at"] == 100
    assert user2["updated_at"] == 200
    assert user2["display_name"] == "Alicia"
    assert user2["email"] == "a@b.com"


def test_set_last_synced_at_creates_user(monkeypatch):
    _force_local_store(monkeypatch)

    user = store.set_last_synced_at("acct", ts=300)
    assert user["jira_account_id"] == "acct"
    assert user["created_at"] == 300
    assert user["last_synced_at"] == 300
    assert user["updated_at"] == 300


def test_upsert_project_dedup(monkeypatch):
    _force_local_store(monkeypatch)

    project = store.upsert_project_for_user(
        "acct",
        project_key="PROJ",
        project_name="Projet",
        source="jira",
        cloud_id="c1",
        now=10,
    )
    assert project["created_at"] == 10
    assert project["updated_at"] == 10
    assert project["mask_type"] == "none"
    assert project["masked_at"] is None

    project2 = store.upsert_project_for_user(
        "acct",
        project_key="PROJ",
        project_name="Projet 2",
        source="manual",
        cloud_id="c1",
        now=20,
    )
    assert project2["created_at"] == 10
    assert project2["updated_at"] == 20
    assert project2["project_name"] == "Projet 2"
    assert project2["source"] == "manual"


def test_invalid_source_and_mask_type(monkeypatch):
    _force_local_store(monkeypatch)

    with pytest.raises(ValueError):
        store.upsert_project_for_user(
            "acct",
            project_key="PROJ",
            project_name="Projet",
            source="invalid",
            now=10,
        )

    with pytest.raises(ValueError):
        store.upsert_project_for_user(
            "acct",
            project_key="PROJ",
            project_name="Projet",
            source="jira",
            mask_type="bad",
            now=10,
        )


def test_set_project_mask(monkeypatch):
    _force_local_store(monkeypatch)

    store.upsert_project_for_user(
        "acct",
        project_key="PROJ",
        project_name="Projet",
        source="jira",
        cloud_id="c1",
        now=10,
    )

    masked = store.set_project_mask(
        "acct",
        project_key="PROJ",
        cloud_id="c1",
        mask_type="definitif",
        now=20,
    )
    assert masked["mask_type"] == "definitif"
    assert masked["masked_at"] == 20

    unmasked = store.set_project_mask(
        "acct",
        project_key="PROJ",
        cloud_id="c1",
        mask_type="none",
        now=30,
    )
    assert unmasked["mask_type"] == "none"
    assert unmasked["masked_at"] is None


def test_set_project_mask_missing(monkeypatch):
    _force_local_store(monkeypatch)

    with pytest.raises(KeyError):
        store.set_project_mask(
            "acct",
            project_key="PROJ",
            cloud_id="c1",
            mask_type="temporaire",
            now=10,
        )


def test_list_projects_sorted(monkeypatch):
    _force_local_store(monkeypatch)

    store.upsert_project_for_user(
        "acct",
        project_key="BETA",
        project_name="Projet B",
        source="jira",
        cloud_id="c1",
        now=10,
    )
    store.upsert_project_for_user(
        "acct",
        project_key="ALPHA",
        project_name="Projet A",
        source="jira",
        cloud_id="c2",
        now=20,
    )

    projects = store.list_projects_for_user("acct")
    assert [p["project_key"] for p in projects] == ["ALPHA", "BETA"]


def test_load_json_invalid_and_non_dict(monkeypatch):
    # invalid JSON -> None
    monkeypatch.setattr(store, "_get_raw", lambda _k: "not-json")
    assert store._load_json("k") is None

    # valid JSON but not a dict -> None
    monkeypatch.setattr(store, "_get_raw", lambda _k: "[]")
    assert store._load_json("k") is None


def test_get_project_for_user(monkeypatch):
    _force_local_store(monkeypatch)

    store.upsert_project_for_user(
        "acct",
        project_key="PROJ",
        project_name="Projet",
        source="jira",
        cloud_id="c1",
        now=10,
    )

    found = store.get_project_for_user("acct", project_key="PROJ", cloud_id="c1")
    assert found is not None
    assert found["project_key"] == "PROJ"


def test_set_project_mask_invalid(monkeypatch):
    _force_local_store(monkeypatch)

    with pytest.raises(ValueError):
        store.set_project_mask(
            "acct",
            project_key="PROJ",
            cloud_id="c1",
            mask_type="bad",
        )
