def test_404_not_found(client):
    response = client.get("/does-not-exist")

    assert response.status_code == 404
    assert response.is_json

    data = response.get_json()
    assert data["error"] == "Not Found"
    assert "Endpoint does not exist" in data["message"]
