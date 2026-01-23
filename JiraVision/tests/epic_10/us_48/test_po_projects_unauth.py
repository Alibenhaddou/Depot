import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Helpers pour simuler une session PO authentifiée

def auth_headers():
    # Simule une session avec un compte Jira valide
    return {
        "Cookie": "sid=test-session",
        # Ajoute d'autres headers/cookies simulant l'état attendu par ensure_session/get_session
    }

# Mocks à adapter selon la logique de session_store et po_project_store

def test_add_project_unauth():
    resp = client.post("/po/projects", json={
        "project_key": "ABC",
        "project_name": "Projet Test"
    })
    assert resp.status_code == 401

def test_mask_project_unauth():
    import json
    payload = json.dumps({"mask_type": "temporaire"})
    resp = client.request(
        "DELETE",
        "/po/projects/ABC",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    assert resp.status_code == 401

def test_refresh_projects_unauth():
    resp = client.post("/po/projects/refresh", json={"reset_definitif": True})
    assert resp.status_code == 401

# TODO: Ajouter des tests avec session valide (mock), cas d'erreur, etc.
