"""Tests for project sync service."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.project_sync import (
    sync_reporter_projects,
    get_hidden_projects_state,
    save_hidden_projects_state,
    hide_project,
    unhide_project,
    clear_temporary_hidden,
)
from app.models.jira import JiraProjectOut, ProjectVisibility


@pytest.mark.asyncio
async def test_sync_reporter_projects_single_instance():
    """Test syncing projects from a single Jira instance."""
    # Mock client
    mock_client = AsyncMock()
    mock_client.search_jql.return_value = {
        "issues": [
            {
                "key": "PROJ-1",
                "fields": {
                    "project": {"key": "PROJ", "name": "Test Project"},
                    "updated": "2024-01-15T10:00:00.000Z",
                },
            },
            {
                "key": "PROJ-2",
                "fields": {
                    "project": {"key": "PROJ", "name": "Test Project"},
                    "updated": "2024-01-16T10:00:00.000Z",
                },
            },
        ],
        "total": 2,
    }
    
    clients = [("cloud1", mock_client)]
    projects = await sync_reporter_projects(clients)
    
    assert len(projects) == 1
    assert projects[0].projectKey == "PROJ"
    assert projects[0].projectName == "Test Project"
    assert projects[0].cloudId == "cloud1"
    assert projects[0].issueCount == 2
    assert projects[0].lastUpdated == "2024-01-16T10:00:00.000Z"
    assert projects[0].visibility == ProjectVisibility.VISIBLE
    assert projects[0].isActive is True
    
    # Verify JQL was correct
    mock_client.search_jql.assert_called_once()
    call_args = mock_client.search_jql.call_args
    jql = call_args[1]["jql"]
    assert "reporter = currentUser()" in jql
    assert "type in (Epic, Story" in jql
    assert "status NOT IN" in jql


@pytest.mark.asyncio
async def test_sync_reporter_projects_multiple_instances():
    """Test syncing projects from multiple Jira instances."""
    mock_client1 = AsyncMock()
    mock_client1.search_jql.return_value = {
        "issues": [
            {
                "key": "PROJ-1",
                "fields": {
                    "project": {"key": "PROJ", "name": "Project 1"},
                    "updated": "2024-01-15T10:00:00.000Z",
                },
            },
        ],
        "total": 1,
    }
    
    mock_client2 = AsyncMock()
    mock_client2.search_jql.return_value = {
        "issues": [
            {
                "key": "OTHER-1",
                "fields": {
                    "project": {"key": "OTHER", "name": "Project 2"},
                    "updated": "2024-01-15T10:00:00.000Z",
                },
            },
        ],
        "total": 1,
    }
    
    clients = [("cloud1", mock_client1), ("cloud2", mock_client2)]
    projects = await sync_reporter_projects(clients)
    
    assert len(projects) == 2
    project_keys = {p.projectKey for p in projects}
    assert "PROJ" in project_keys
    assert "OTHER" in project_keys


@pytest.mark.asyncio
async def test_sync_reporter_projects_with_hidden():
    """Test that hidden projects get the correct visibility state."""
    mock_client = AsyncMock()
    mock_client.search_jql.return_value = {
        "issues": [
            {
                "key": "PROJ-1",
                "fields": {
                    "project": {"key": "PROJ", "name": "Test Project"},
                    "updated": "2024-01-15T10:00:00.000Z",
                },
            },
        ],
        "total": 1,
    }
    
    clients = [("cloud1", mock_client)]
    hidden = {"PROJ": "hidden_permanent"}
    projects = await sync_reporter_projects(clients, hidden)
    
    assert len(projects) == 1
    assert projects[0].visibility == ProjectVisibility.HIDDEN_PERMANENT


@pytest.mark.asyncio
async def test_sync_reporter_projects_empty_response():
    """Test syncing with no issues found."""
    mock_client = AsyncMock()
    mock_client.search_jql.return_value = {
        "issues": [],
        "total": 0,
    }
    
    clients = [("cloud1", mock_client)]
    projects = await sync_reporter_projects(clients)
    
    assert len(projects) == 0


@pytest.mark.asyncio
async def test_sync_reporter_projects_client_error():
    """Test that client errors don't fail the entire sync."""
    mock_client1 = AsyncMock()
    mock_client1.search_jql.side_effect = Exception("API error")
    
    mock_client2 = AsyncMock()
    mock_client2.search_jql.return_value = {
        "issues": [
            {
                "key": "PROJ-1",
                "fields": {
                    "project": {"key": "PROJ", "name": "Test Project"},
                    "updated": "2024-01-15T10:00:00.000Z",
                },
            },
        ],
        "total": 1,
    }
    
    clients = [("cloud1", mock_client1), ("cloud2", mock_client2)]
    projects = await sync_reporter_projects(clients)
    
    # Should get results from cloud2 only
    assert len(projects) == 1
    assert projects[0].cloudId == "cloud2"


@pytest.mark.asyncio
async def test_sync_reporter_projects_pagination():
    """Test handling pagination with next_token."""
    mock_client = AsyncMock()
    # Return data with nextPageToken to trigger pagination code path
    mock_client.search_jql.return_value = {
        "issues": [
            {
                "key": "PROJ-1",
                "fields": {
                    "project": {"key": "PROJ", "name": "Test Project"},
                    "updated": "2024-01-15T10:00:00.000Z",
                },
            },
        ],
        "total": 100,  # More than fetched
        "nextPageToken": "token123",
    }
    
    clients = [("cloud1", mock_client)]
    projects = await sync_reporter_projects(clients)
    
    # Should break when next_token is present
    assert len(projects) == 1
    assert projects[0].projectKey == "PROJ"


@pytest.mark.asyncio
async def test_sync_reporter_projects_missing_project_key():
    """Test handling issues without project key."""
    mock_client = AsyncMock()
    mock_client.search_jql.return_value = {
        "issues": [
            {
                "key": "PROJ-1",
                "fields": {
                    "project": {},  # Missing key
                    "updated": "2024-01-15T10:00:00.000Z",
                },
            },
            {
                "key": "PROJ-2",
                "fields": {
                    "project": {"key": "VALID", "name": "Valid Project"},
                    "updated": "2024-01-15T10:00:00.000Z",
                },
            },
        ],
        "total": 2,
    }
    
    clients = [("cloud1", mock_client)]
    projects = await sync_reporter_projects(clients)
    
    # Should only get the valid project
    assert len(projects) == 1
    assert projects[0].projectKey == "VALID"


def test_get_hidden_projects_state():
    """Test getting hidden projects from session."""
    session = {"hidden_projects": {"PROJ1": "hidden_permanent"}}
    hidden = get_hidden_projects_state(session)
    assert hidden == {"PROJ1": "hidden_permanent"}


def test_get_hidden_projects_state_empty():
    """Test getting hidden projects from empty session."""
    session = {}
    hidden = get_hidden_projects_state(session)
    assert hidden == {}


def test_save_hidden_projects_state():
    """Test saving hidden projects to session."""
    session = {}
    hidden = {"PROJ1": "hidden_permanent"}
    save_hidden_projects_state(session, hidden)
    assert session["hidden_projects"] == hidden


def test_hide_project():
    """Test hiding a project."""
    session = {}
    hide_project(session, "PROJ1", permanent=True)
    assert session["hidden_projects"]["PROJ1"] == "hidden_permanent"


def test_hide_project_temporary():
    """Test hiding a project temporarily."""
    session = {}
    hide_project(session, "PROJ1", permanent=False)
    assert session["hidden_projects"]["PROJ1"] == "hidden_temporary"


def test_unhide_project():
    """Test unhiding a project."""
    session = {"hidden_projects": {"PROJ1": "hidden_permanent"}}
    unhide_project(session, "PROJ1")
    assert "PROJ1" not in session["hidden_projects"]


def test_unhide_project_not_hidden():
    """Test unhiding a project that wasn't hidden."""
    session = {"hidden_projects": {}}
    unhide_project(session, "PROJ1")
    assert session["hidden_projects"] == {}


def test_clear_temporary_hidden():
    """Test clearing temporarily hidden projects."""
    session = {
        "hidden_projects": {
            "PROJ1": "hidden_permanent",
            "PROJ2": "hidden_temporary",
            "PROJ3": "hidden_temporary",
        }
    }
    clear_temporary_hidden(session)
    assert session["hidden_projects"] == {"PROJ1": "hidden_permanent"}


def test_clear_temporary_hidden_empty():
    """Test clearing temporary hidden with no hidden projects."""
    session = {"hidden_projects": {}}
    clear_temporary_hidden(session)
    assert session["hidden_projects"] == {}
