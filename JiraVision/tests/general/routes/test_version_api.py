from fastapi.testclient import TestClient

from app.main import app


def test_api_version_endpoint():
    client = TestClient(app)
    r = client.get("/version")
    assert r.status_code == 200
    data = r.json()
    assert data.get("service") == "api"
    assert isinstance(data.get("version"), str)
    assert isinstance(data.get("python_version"), str)
    assert isinstance(data.get("build_date"), str)
