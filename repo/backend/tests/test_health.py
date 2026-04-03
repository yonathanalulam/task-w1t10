def test_liveness(client):
    response = client.get("/api/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readiness(client):
    response = client.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
