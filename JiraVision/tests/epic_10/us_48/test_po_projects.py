import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

# Fixtures et helpers à compléter selon la gestion d'auth/session

def test_list_projects_unauth():
    resp = client.get("/po/projects")
    assert resp.status_code == 401
    assert "Connecte-toi" in resp.text or "Compte Jira" in resp.text

# TODO: Ajouter des tests avec session valide (mock), ajout, masquage, refresh, erreurs, etc.
