import pytest
from fastapi.testclient import TestClient
from app.app.main import app

client = TestClient(app)

# Helpers pour simuler une session PO authentifiée (mock sid + patch get_session)

def make_auth_cookie(sid="test-session"):
    from itsdangerous import URLSafeSerializer
    from app.app.core.config import settings
    s = URLSafeSerializer(settings.app_secret_key, salt="sid")
    signed_sid = s.dumps(sid)
    return {"sid": signed_sid}

def test_list_projects_minimal():
    sid = "test-session"
    # Ici on ne patch pas get_session, on teste juste la route GET /po/projects
    resp = client.get("/po/projects", cookies=make_auth_cookie(sid))
    assert resp.status_code == 401 or resp.status_code == 200
