def test_liveness(client):
    response = client.get("/api/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness(client):
    response = client.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


def test_root_returns_minimal_service_status(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "environment" not in response.json()
    assert "service" not in response.json()
    assert "docs" not in response.json()
