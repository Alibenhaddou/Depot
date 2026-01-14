import types
import time

from fastapi import Response
import pytest

from app.auth import session_store


class DummyRequest:
    def __init__(self, cookies=None, query_params=None):
        self.cookies = cookies or {}
        self.query_params = query_params or {}


def test_get_sid_absent():
    req = DummyRequest()
    assert session_store.get_sid(req) is None


def test_set_and_get_sid_cookie_roundtrip(monkeypatch):
    # Ensure the serializer/dump works and get_sid recovers it
    resp = Response()
    sid = "my-session"
    session_store.set_sid_cookie(resp, sid)

    # The response will have Set-Cookie header; extract cookie value
    header = resp.headers.get("set-cookie")
    assert header is not None

    # emulate request with that cookie
    # format is like: sid=<signed>; Path=/; HttpOnly; Max-Age=...
    cookie_val = header.split(";", 1)[0].split("=", 1)[1]
    req = DummyRequest(cookies={"sid": cookie_val})
    assert session_store.get_sid(req) == sid


def test_ensure_session_creates_when_missing(monkeypatch):
    req = DummyRequest(cookies={})
    resp = Response()

    called = {}

    def fake_set_session(sid, sess):
        called["sid"] = sid
        called["sess"] = sess

    monkeypatch.setattr(session_store, "set_session", fake_set_session)
    monkeypatch.setattr(session_store, "_new_session_id", lambda: "fixed-sid")

    out = session_store.ensure_session(req, resp)
    assert out == "fixed-sid"
    assert called["sid"] == "fixed-sid"
    assert "created_at" in called["sess"]


def test_ensure_session_refreshes_missing_redis(monkeypatch):
    req = DummyRequest(cookies={})
    resp = Response()

    # simulate cookie present but redis missing
    monkeypatch.setattr(session_store, "get_sid", lambda r: "sid-1")
    monkeypatch.setattr(session_store, "get_session", lambda s: None)

    calls = {"set_session": False}

    def fake_set_session(sid, sess):
        calls["set_session"] = True

    monkeypatch.setattr(session_store, "set_session", fake_set_session)

    session_store.ensure_session(req, resp)
    # because get_session returns None by our stub, ensure set_session called
    assert calls["set_session"]


def test_require_session_raises_when_no_cookie(monkeypatch):
    req = DummyRequest(cookies={})
    with pytest.raises(Exception):
        session_store.require_session(req)


def test_destroy_session_calls_delete(monkeypatch):
    req = DummyRequest(cookies={})
    resp = Response()

    monkeypatch.setattr(session_store, "get_sid", lambda r: "sid-2")
    called = {}

    def fake_delete_session(sid):
        called["deleted"] = sid

    monkeypatch.setattr(session_store, "delete_session", fake_delete_session)

    session_store.destroy_session(req, resp)
    assert called["deleted"] == "sid-2"
