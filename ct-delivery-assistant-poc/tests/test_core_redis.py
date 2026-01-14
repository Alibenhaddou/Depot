import json
import types


from app.core import redis as core_redis
from app.core import config


def test_key():
    assert core_redis._key("abc") == "session:abc"


def test_get_session_none_when_missing(monkeypatch):
    fake = types.SimpleNamespace(get=lambda k: None)
    monkeypatch.setattr(core_redis, "redis_client", fake)
    assert core_redis.get_session("sid") is None


def test_get_session_parses_and_refreshes_ttl(monkeypatch):
    stored = {"user": "bob"}

    def fake_get(k):
        return json.dumps(stored)

    called = {}

    def fake_expire(k, seconds):
        called["expire"] = (k, seconds)

    fake = types.SimpleNamespace(get=fake_get, expire=fake_expire)
    monkeypatch.setattr(core_redis, "redis_client", fake)
    # override settings to known value
    monkeypatch.setattr(config.settings, "session_max_age_seconds", 12345)

    out = core_redis.get_session("sid")
    assert out == stored
    assert called["expire"] == ("session:sid", 12345)


def test_set_session_calls_set(monkeypatch):
    captured = {}

    def fake_set(k, v, ex=None):
        captured["k"] = k
        captured["v"] = v
        captured["ex"] = ex

    fake = types.SimpleNamespace(set=fake_set)
    monkeypatch.setattr(core_redis, "redis_client", fake)
    monkeypatch.setattr(config.settings, "session_max_age_seconds", 42)

    core_redis.set_session("sid", {"hello": "world"})
    assert captured["k"] == "session:sid"
    assert json.loads(captured["v"]) == {"hello": "world"}
    assert captured["ex"] == 42


def test_delete_session_calls_delete(monkeypatch):
    called = {}

    def fake_delete(k):
        called["k"] = k

    fake = types.SimpleNamespace(delete=fake_delete)
    monkeypatch.setattr(core_redis, "redis_client", fake)

    core_redis.delete_session("sid")
    assert called["k"] == "session:sid"
