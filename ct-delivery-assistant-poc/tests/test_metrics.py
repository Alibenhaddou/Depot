from fastapi.testclient import TestClient

from app.main import create_app


def test_metrics_endpoint():
    app = create_app()
    client = TestClient(app)
    r = client.get("/metrics")
    assert r.status_code == 200
    assert "http_requests_total" in r.text


def test_root_redirect():
    app = create_app()
    client = TestClient(app)
    r = client.get("/", follow_redirects=False)
    assert r.status_code in (302, 307)
