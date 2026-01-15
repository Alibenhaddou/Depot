import sys
import pathlib
import pytest
from fastapi.testclient import TestClient

# Ensure our local services/ai_service is discoverable and import the package 'ai_app'
root = pathlib.Path(__file__).resolve().parents[1]
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

import ai_app.main as ai_main

from fastapi.testclient import TestClient

client = TestClient(ai_main.app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.text == "ok"


def test_summarize_jql():
    r = client.post("/ai/summarize-jql", json={"jql": "project=PROJ", "max_results": 1})
    assert r.status_code == 200
    data = r.json()
    assert "cloud_id" in data
    assert data["count"] == 1
    assert "result" in data


def test_analyze_issue():
    r = client.post("/ai/analyze-issue", json={"issue_key": "PROJ-1"})
    assert r.status_code == 200
    data = r.json()
    assert data["result"] == "Analyse exemple"
