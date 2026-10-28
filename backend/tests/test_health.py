from fastapi import status


def test_health_endpoint(client):
    """Test GET /api/health returns 200 with status success."""
    response = client.get("/api/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
    assert "CareerPilot AI" in data["service"]


def test_api_v1_health_endpoint(client):
    """Test GET /api/v1/health returns 200 with status success."""
    response = client.get("/api/v1/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "success"
