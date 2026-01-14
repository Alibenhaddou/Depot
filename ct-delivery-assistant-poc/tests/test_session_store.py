import time
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from starlette.responses import Response

from app.auth import session_store as ss


def _extract_cookie_value(set_cookie_header: str) -> str:
    # header like: sid=<value>; Path=/; HttpOnly; SameSite=lax
    return set_cookie_header.split(";", 1)[0].split("=", 1)[1]


def test_get_sid_no_cookie():
    req = SimpleNamespace(cookies={})
    assert ss.get_sid(req) is None


def test_set_and_get_sid_cookie_roundtrip():
    resp = Response()
    ss.set_sid_cookie(resp, "mysid")
    header = resp.headers.get("set-cookie")
    assert header is not None
    cookie_val = _extract_cookie_value(header)

    req = SimpleNamespace(cookies={"sid": cookie_val})
    sid = ss.get_sid(req)
    assert sid == "mysid"


def test_get_sid_bad_signature():
    req = SimpleNamespace(cookies={"sid": "not-a-valid"})
    assert ss.get_sid(req) is None


def test_ensure_session_creates_when_missing(monkeypatch):
    called = {}

    def fake_set_session(sid, sess):
        called["sid"] = sid
        called["sess"] = sess

    monkeypatch.setattr(ss, "set_session", fake_set_session)

    req = SimpleNamespace(cookies={})
    resp = Response()

    sid = ss.ensure_session(req, resp)
    assert sid
    assert called.get("sid") == sid
    assert isinstance(called.get("sess"), dict)
    # cookie set
    assert resp.headers.get("set-cookie") is not None


def test_ensure_session_refreshes_when_session_missing(monkeypatch):
    # create a valid cookie
    resp = Response()
    ss.set_sid_cookie(resp, "existingsid")
    cookie_val = _extract_cookie_value(resp.headers.get("set-cookie"))

    # get_session returns None -> should call set_session
    called = {}

    def fake_get_session(sid):
        return None

    def fake_set_session(sid, sess):
        called["sid"] = sid

    monkeypatch.setattr(ss, "get_session", fake_get_session)
    monkeypatch.setattr(ss, "set_session", fake_set_session)

    req = SimpleNamespace(cookies={"sid": cookie_val})
    resp2 = Response()

    sid = ss.ensure_session(req, resp2)
    assert sid == "existingsid"
    assert called.get("sid") == "existingsid"


def test_require_session_errors(monkeypatch):
    req = SimpleNamespace(cookies={})
    with pytest.raises(HTTPException):
        ss.require_session(req)

    # present sid but no session
    resp = Response()
    ss.set_sid_cookie(resp, "s2")
    cookie_val = _extract_cookie_value(resp.headers.get("set-cookie"))

    def fake_get_session_none(sid):
        return None

    monkeypatch.setattr(ss, "get_session", fake_get_session_none)

    req2 = SimpleNamespace(cookies={"sid": cookie_val})
    with pytest.raises(HTTPException):
        ss.require_session(req2)


def test_destroy_session_calls_delete_and_deletes_cookie(monkeypatch):
    called = {"deleted": False}

    def fake_delete(sid):
        called["deleted"] = True

    monkeypatch.setattr(ss, "delete_session", fake_delete)

    resp = Response()
    # put a sid in request
    ss.set_sid_cookie(resp, "tosid")
    cookie_val = _extract_cookie_value(resp.headers.get("set-cookie"))

    req = SimpleNamespace(cookies={"sid": cookie_val})
    resp2 = Response()

    ss.destroy_session(req, resp2)
    assert called["deleted"]
    # cookie must be set to deleted (set-cookie present)
    assert resp2.headers.get("set-cookie") is not None


def test_require_session_success(monkeypatch):
    resp = Response()
    ss.set_sid_cookie(resp, "ok-sid")
    cookie_val = _extract_cookie_value(resp.headers.get("set-cookie"))

    # get_session returns a dict -> should succeed
    monkeypatch.setattr(ss, "get_session", lambda sid: {"created_at": 1})

    req = SimpleNamespace(cookies={"sid": cookie_val})
    sid = ss.require_session(req)
    assert sid == "ok-sid"
