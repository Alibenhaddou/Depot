from types import SimpleNamespace


from app.routes import auth as auth_mod
from app.core.config import settings


def test_redirect_uri_prefers_env(monkeypatch):
    monkeypatch.setattr(settings, "atlassian_redirect_uri", "http://env/cb")
    req = SimpleNamespace()
    assert auth_mod._redirect_uri(req) == "http://env/cb"


def test_redirect_uri_builds_from_request(monkeypatch):
    # ensure attr not set
    monkeypatch.setattr(settings, "atlassian_redirect_uri", "", raising=False)

    class Req:
        def url_for(self, name):
            return "http://host/cb"

    assert auth_mod._redirect_uri(Req()) == "http://host/cb"


def test_expected_state_from_cookie_valid_and_bad(monkeypatch):
    class Req:
        cookies = {}

    # good cookie
    s = auth_mod.state_serializer.dumps("s123")
    r = Req()
    r.cookies = {"oauth_state": s}
    assert auth_mod._expected_state_from_cookie(r) == "s123"

    # bad cookie
    r2 = Req()
    r2.cookies = {"oauth_state": "bad"}
    assert auth_mod._expected_state_from_cookie(r2) is None


def test_pick_jira_resources_substring_scopes():
    resources = [
        {"id": "1", "url": "u", "scopes": ["something:jira:read"]},
        {"id": "2", "url": "u", "scopes": ["other:scope"]},
    ]

    out = auth_mod._pick_jira_resources(resources)
    assert len(out) == 1
    assert out[0]["id"] == "1"
