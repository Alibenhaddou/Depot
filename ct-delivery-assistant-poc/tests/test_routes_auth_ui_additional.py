from fastapi.testclient import TestClient
from starlette.responses import Response

from app.main import create_app

app = create_app()
client = TestClient(app)


def test_auth_page_sets_cookie(monkeypatch):
    # when ensure_session is mocked we only verify HTML renders
    monkeypatch.setattr("app.routes.auth_ui.ensure_session", lambda req, resp: "sid")

    r = client.get("/auth")
    assert r.status_code == 200
    assert "<html" in r.text.lower()


def test_auth_page_cookie_is_set_when_real_ensure(monkeypatch):
    # allow ensure_session to run but stub out backend set_session in session_store
    called = {}

    def fake_set_session(sid, sess):
        called["sid"] = sid

    import app.auth.session_store as ss

    monkeypatch.setattr(ss, "set_session", fake_set_session)
    r = client.get("/auth")
    assert r.status_code == 200
    # cookie sid present in response headers
    assert any("sid=" in c for c in r.headers.get_list("set-cookie"))


def test_auth_state_logged_in_and_logged_out(monkeypatch):
    # logged out
    monkeypatch.setattr("app.routes.auth_ui.ensure_session", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.auth_ui.get_session", lambda sid: {})
    r = client.get("/auth/state")
    assert r.status_code == 200
    assert r.json()["logged_in"] is False

    # logged in
    monkeypatch.setattr(
        "app.routes.auth_ui.get_session", lambda sid: {"access_token": "t"}
    )
    r2 = client.get("/auth/state")
    assert r2.status_code == 200
    assert r2.json()["logged_in"] is True
