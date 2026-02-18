def test_index_success(client):
    response = client.get("/")

    assert response.status_code == 200

    data = response.get_json()

    # Service info
    assert "service" in data
    assert data["service"]["name"] == "devops-info-service"
    assert data["service"]["framework"] == "Flask"

    # System info
    assert "system" in data
    assert "hostname" in data["system"]
    assert isinstance(data["system"]["cpu_count"], int)

    # Runtime info
    assert "runtime" in data
    assert data["runtime"]["timezone"] == "UTC"
    assert data["runtime"]["uptime_seconds"] >= 0

    # Request info
    assert "request" in data
    assert data["request"]["method"] == "GET"
    assert data["request"]["path"] == "/"

    # Endpoints list
    assert isinstance(data["endpoints"], list)
    assert any(e["path"] == "/health" for e in data["endpoints"])
