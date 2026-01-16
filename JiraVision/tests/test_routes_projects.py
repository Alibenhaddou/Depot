"""Tests for project sync routes."""

from datetime import datetime
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import create_app
from app.models.jira import JiraProjectOut, ProjectVisibility

app = create_app()
client = TestClient(app)


def test_get_reporter_projects_not_logged_in(monkeypatch):
    """Test getting projects when not logged in."""
    monkeypatch.setattr("app.routes.jira._ensure_sid", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.jira.get_session", lambda sid: {})
    
    r = client.get("/jira/projects/reporter")
    assert r.status_code == 401
    assert "Connecte-toi" in r.json()["detail"]


def test_get_reporter_projects_cached(monkeypatch):
    """Test getting cached reporter projects."""
    monkeypatch.setattr("app.routes.jira._ensure_sid", lambda req, resp: "sid")
    
    cached_projects = [
        {
            "projectKey": "PROJ",
            "projectName": "Test Project",
            "cloudId": "cloud1",
            "issueCount": 2,
            "lastUpdated": "2024-01-15T10:00:00.000Z",
            "visibility": "visible",
            "isActive": True,
        }
    ]
    
    session = {
        "tokens_by_cloud": {"cloud1": {"access_token": "token"}},
        "cloud_ids": ["cloud1"],
        "reporter_projects": cached_projects,
        "reporter_projects_sync_at": "2024-01-15T10:00:00.000Z",
    }
    
    monkeypatch.setattr("app.routes.jira.get_session", lambda sid: session)
    
    r = client.get("/jira/projects/reporter")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 1
    assert data["projects"][0]["projectKey"] == "PROJ"
    assert data["lastSyncAt"] == "2024-01-15T10:00:00.000Z"


def test_get_reporter_projects_triggers_sync(monkeypatch):
    """Test that getting projects triggers sync when not cached."""
    monkeypatch.setattr("app.routes.jira._ensure_sid", lambda req, resp: "sid")
    
    session = {
        "tokens_by_cloud": {"cloud1": {"access_token": "token"}},
        "cloud_ids": ["cloud1"],
    }
    
    monkeypatch.setattr("app.routes.jira.get_session", lambda sid: session)
    monkeypatch.setattr("app.routes.jira.set_session", lambda sid, sess: None)
    
    mock_project = JiraProjectOut(
        projectKey="PROJ",
        projectName="Test Project",
        cloudId="cloud1",
        issueCount=1,
        lastUpdated="2024-01-15T10:00:00.000Z",
        visibility=ProjectVisibility.VISIBLE,
        isActive=True,
    )
    
    with patch("app.routes.jira.sync_reporter_projects", return_value=[mock_project]) as mock_sync:
        with patch("app.routes.jira.JiraClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            r = client.get("/jira/projects/reporter")
            assert r.status_code == 200


def test_sync_reporter_projects_manual(monkeypatch):
    """Test manual sync of reporter projects."""
    monkeypatch.setattr("app.routes.jira._ensure_sid", lambda req, resp: "sid")
    
    session = {
        "tokens_by_cloud": {"cloud1": {"access_token": "token"}},
        "cloud_ids": ["cloud1"],
        "hidden_projects": {"OLD": "hidden_temporary"},
    }
    
    monkeypatch.setattr("app.routes.jira.get_session", lambda sid: session)
    
    set_session_calls = []
    def mock_set_session(sid, sess):
        set_session_calls.append(sess.copy())
    
    monkeypatch.setattr("app.routes.jira.set_session", mock_set_session)
    
    mock_project = JiraProjectOut(
        projectKey="PROJ",
        projectName="Test Project",
        cloudId="cloud1",
        issueCount=1,
        lastUpdated="2024-01-15T10:00:00.000Z",
        visibility=ProjectVisibility.VISIBLE,
        isActive=True,
    )
    
    with patch("app.routes.jira.sync_reporter_projects", return_value=[mock_project]) as mock_sync:
        with patch("app.routes.jira.JiraClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            r = client.post("/jira/projects/sync")
            assert r.status_code == 200
            data = r.json()
            assert data["total"] == 1
            assert data["projects"][0]["projectKey"] == "PROJ"
            
            # Verify temporary hidden was cleared
            assert len(set_session_calls) > 0
            final_session = set_session_calls[-1]
            assert "OLD" not in final_session.get("hidden_projects", {})


def test_sync_reporter_projects_no_instances(monkeypatch):
    """Test sync when no Jira instances are connected."""
    monkeypatch.setattr("app.routes.jira._ensure_sid", lambda req, resp: "sid")
    
    session = {
        "tokens_by_cloud": {"cloud1": {"access_token": "token"}},
        "cloud_ids": [],  # No active cloud_ids
    }
    
    monkeypatch.setattr("app.routes.jira.get_session", lambda sid: session)
    monkeypatch.setattr("app.routes.jira.set_session", lambda sid, sess: None)
    
    r = client.post("/jira/projects/sync")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 0
    assert data["projects"] == []


def test_hide_project_temporary(monkeypatch):
    """Test hiding a project temporarily."""
    monkeypatch.setattr("app.routes.jira._ensure_sid", lambda req, resp: "sid")
    
    session = {
        "tokens_by_cloud": {"cloud1": {"access_token": "token"}},
        "cloud_ids": ["cloud1"],
        "reporter_projects": [
            {
                "projectKey": "PROJ",
                "projectName": "Test Project",
                "cloudId": "cloud1",
                "issueCount": 1,
                "lastUpdated": "2024-01-15T10:00:00.000Z",
                "visibility": "visible",
                "isActive": True,
            }
        ],
    }
    
    monkeypatch.setattr("app.routes.jira.get_session", lambda sid: session)
    
    set_session_calls = []
    def mock_set_session(sid, sess):
        set_session_calls.append(sess.copy())
    
    monkeypatch.setattr("app.routes.jira.set_session", mock_set_session)
    
    r = client.post("/jira/projects/PROJ/hide", params={"permanent": False})
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True
    assert data["projectKey"] == "PROJ"
    assert data["hidden"] is True
    assert data["permanent"] is False
    
    # Verify project was removed from cached list
    final_session = set_session_calls[-1]
    assert len(final_session["reporter_projects"]) == 0
    assert final_session["hidden_projects"]["PROJ"] == "hidden_temporary"


def test_hide_project_permanent(monkeypatch):
    """Test hiding a project permanently."""
    monkeypatch.setattr("app.routes.jira._ensure_sid", lambda req, resp: "sid")
    
    session = {
        "tokens_by_cloud": {"cloud1": {"access_token": "token"}},
        "cloud_ids": ["cloud1"],
        "reporter_projects": [
            {
                "projectKey": "PROJ",
                "projectName": "Test Project",
                "cloudId": "cloud1",
                "issueCount": 1,
                "lastUpdated": "2024-01-15T10:00:00.000Z",
                "visibility": "visible",
                "isActive": True,
            }
        ],
    }
    
    monkeypatch.setattr("app.routes.jira.get_session", lambda sid: session)
    
    set_session_calls = []
    def mock_set_session(sid, sess):
        set_session_calls.append(sess.copy())
    
    monkeypatch.setattr("app.routes.jira.set_session", mock_set_session)
    
    r = client.post("/jira/projects/PROJ/hide", params={"permanent": True})
    assert r.status_code == 200
    data = r.json()
    assert data["permanent"] is True
    
    # Verify hidden state
    final_session = set_session_calls[-1]
    assert final_session["hidden_projects"]["PROJ"] == "hidden_permanent"


def test_unhide_project(monkeypatch):
    """Test unhiding a project."""
    monkeypatch.setattr("app.routes.jira._ensure_sid", lambda req, resp: "sid")
    
    session = {
        "tokens_by_cloud": {"cloud1": {"access_token": "token"}},
        "cloud_ids": ["cloud1"],
        "hidden_projects": {"PROJ": "hidden_permanent"},
        "reporter_projects": [],
    }
    
    monkeypatch.setattr("app.routes.jira.get_session", lambda sid: session)
    monkeypatch.setattr("app.routes.jira.set_session", lambda sid, sess: None)
    
    mock_project = JiraProjectOut(
        projectKey="PROJ",
        projectName="Test Project",
        cloudId="cloud1",
        issueCount=1,
        lastUpdated="2024-01-15T10:00:00.000Z",
        visibility=ProjectVisibility.VISIBLE,
        isActive=True,
    )
    
    with patch("app.routes.jira.sync_reporter_projects", return_value=[mock_project]) as mock_sync:
        with patch("app.routes.jira.JiraClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            r = client.post("/jira/projects/PROJ/unhide")
            assert r.status_code == 200
            data = r.json()
            assert data["ok"] is True
            assert data["projectKey"] == "PROJ"
            assert data["hidden"] is False


def test_hide_project_not_logged_in(monkeypatch):
    """Test hiding project when not logged in."""
    monkeypatch.setattr("app.routes.jira._ensure_sid", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.jira.get_session", lambda sid: {})
    
    r = client.post("/jira/projects/PROJ/hide")
    assert r.status_code == 401


def test_sync_reporter_projects_sync_error(monkeypatch):
    """Test handling sync errors."""
    monkeypatch.setattr("app.routes.jira._ensure_sid", lambda req, resp: "sid")
    
    session = {
        "tokens_by_cloud": {"cloud1": {"access_token": "token"}},
        "cloud_ids": ["cloud1"],
    }
    
    monkeypatch.setattr("app.routes.jira.get_session", lambda sid: session)
    monkeypatch.setattr("app.routes.jira.set_session", lambda sid, sess: None)
    
    with patch("app.routes.jira.sync_reporter_projects", side_effect=Exception("Sync error")) as mock_sync:
        with patch("app.routes.jira.JiraClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            r = client.post("/jira/projects/sync")
            assert r.status_code == 502
            assert "Erreur lors de la synchronisation" in r.json()["detail"]
            
            # Verify client was closed
            mock_client.aclose.assert_called()


def test_unhide_project_not_logged_in(monkeypatch):
    """Test unhiding project when not logged in."""
    monkeypatch.setattr("app.routes.jira._ensure_sid", lambda req, resp: "sid")
    monkeypatch.setattr("app.routes.jira.get_session", lambda sid: {})
    
    r = client.post("/jira/projects/PROJ/unhide")
    assert r.status_code == 401
