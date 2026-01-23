import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from app.main import create_app
from app.core import po_project_store


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def mock_session():
    """Mock session with authentication."""
    return {
        "access_token": "test_token",
        "jira_account_id": "test_user_id",
        "jira_display_name": "Test User",
        "jira_email": "test@example.com",
        "cloud_ids": ["cloud1"],
        "tokens_by_cloud": {
            "cloud1": {
                "access_token": "test_token",
                "site_url": "https://test.atlassian.net"
            }
        }
    }


def _force_local_store(monkeypatch):
    """Force use of local in-memory store instead of Redis."""
    def _boom(*_args, **_kwargs):
        raise RuntimeError("redis down")

    monkeypatch.setattr(po_project_store.redis_client, "get", _boom)
    monkeypatch.setattr(po_project_store.redis_client, "set", _boom)
    po_project_store._local_store.clear()


def test_get_projects_unauthenticated(client):
    """Test GET /po/projects without authentication."""
    with patch("app.routes.po.get_session") as mock_get_session:
        mock_get_session.return_value = {}
        
        response = client.get("/po/projects")
        assert response.status_code == 401


def test_get_projects_empty(client, mock_session, monkeypatch):
    """Test GET /po/projects with no projects."""
    _force_local_store(monkeypatch)
    
    with patch("app.routes.po.get_session") as mock_get_session, \
         patch("app.routes.po.ensure_session") as mock_ensure:
        mock_get_session.return_value = mock_session
        mock_ensure.return_value = "test_sid"
        
        response = client.get("/po/projects")
        assert response.status_code == 200
        
        data = response.json()
        assert "projects" in data
        assert "inactive_projects" in data
        assert isinstance(data["projects"], list)
        assert isinstance(data["inactive_projects"], list)


def test_get_projects_with_data(client, mock_session, monkeypatch):
    """Test GET /po/projects with existing projects."""
    _force_local_store(monkeypatch)
    
    # Add test data
    po_project_store.upsert_project_for_user(
        "test_user_id",
        project_key="PROJ1",
        project_name="Project 1",
        source="jira",
        cloud_id="cloud1",
        mask_type="none",
        is_active=True
    )
    
    po_project_store.upsert_project_for_user(
        "test_user_id",
        project_key="PROJ2",
        project_name="Project 2",
        source="manual",
        cloud_id="cloud1",
        mask_type="none",
        is_active=False
    )
    
    with patch("app.routes.po.get_session") as mock_get_session, \
         patch("app.routes.po.ensure_session") as mock_ensure:
        mock_get_session.return_value = mock_session
        mock_ensure.return_value = "test_sid"
        
        response = client.get("/po/projects")
        assert response.status_code == 200
        
        data = response.json()
        assert len(data["projects"]) == 1
        assert len(data["inactive_projects"]) == 1
        assert data["projects"][0]["project_key"] == "PROJ1"
        assert data["inactive_projects"][0]["project_key"] == "PROJ2"


def test_get_projects_filters_masked(client, mock_session, monkeypatch):
    """Test that masked projects are filtered out."""
    _force_local_store(monkeypatch)
    
    # Add test data with masked project
    po_project_store.upsert_project_for_user(
        "test_user_id",
        project_key="PROJ1",
        project_name="Project 1",
        source="jira",
        cloud_id="cloud1",
        mask_type="none",
        is_active=True
    )
    
    po_project_store.upsert_project_for_user(
        "test_user_id",
        project_key="PROJ2",
        project_name="Project 2",
        source="jira",
        cloud_id="cloud1",
        mask_type="definitif",
        is_active=True
    )
    
    with patch("app.routes.po.get_session") as mock_get_session, \
         patch("app.routes.po.ensure_session") as mock_ensure:
        mock_get_session.return_value = mock_session
        mock_ensure.return_value = "test_sid"
        
        response = client.get("/po/projects")
        assert response.status_code == 200
        
        data = response.json()
        # Only PROJ1 should be visible, PROJ2 is masked
        assert len(data["projects"]) == 1
        assert data["projects"][0]["project_key"] == "PROJ1"


def test_add_project(client, mock_session, monkeypatch):
    """Test POST /po/projects to add a manual project."""
    _force_local_store(monkeypatch)
    
    with patch("app.routes.po.get_session") as mock_get_session, \
         patch("app.routes.po.ensure_session") as mock_ensure:
        mock_get_session.return_value = mock_session
        mock_ensure.return_value = "test_sid"
        
        response = client.post(
            "/po/projects",
            json={
                "project_key": "MANUAL1",
                "project_name": "Manual Project",
                "cloud_id": "cloud1"
            }
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["project_key"] == "MANUAL1"
        assert data["source"] == "manual"


def test_mask_project(client, mock_session, monkeypatch):
    """Test DELETE /po/projects/{project_key} to mask a project."""
    _force_local_store(monkeypatch)
    
    # Add test project
    po_project_store.upsert_project_for_user(
        "test_user_id",
        project_key="PROJ1",
        project_name="Project 1",
        source="jira",
        cloud_id="cloud1",
        mask_type="none",
        is_active=True
    )
    
    with patch("app.routes.po.get_session") as mock_get_session, \
         patch("app.routes.po.ensure_session") as mock_ensure:
        mock_get_session.return_value = mock_session
        mock_ensure.return_value = "test_sid"
        
        response = client.request(
            "DELETE",
            "/po/projects/PROJ1",
            json={"mask_type": "temporaire"}
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["mask_type"] == "temporaire"
