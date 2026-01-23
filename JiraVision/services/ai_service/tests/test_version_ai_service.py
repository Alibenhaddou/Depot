from fastapi.testclient import TestClient

from ai_app.main import app


def test_ai_service_version_endpoint():
    client = TestClient(app)
    r = client.get("/version")
    assert r.status_code == 200
    data = r.json()
    assert data.get("service") == "ai-service"
    assert isinstance(data.get("version"), str)
    assert isinstance(data.get("python_version"), str)
    assert isinstance(data.get("build_date"), str)
