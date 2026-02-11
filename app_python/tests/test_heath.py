def test_health_success(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.is_json

    data = response.get_json()

    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert data["uptime_seconds"] >= 0
