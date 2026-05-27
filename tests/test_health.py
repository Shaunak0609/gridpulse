"""
Tests for the root and health endpoints.
These endpoints do not touch the database.
"""


def test_root_returns_200(client):
    response = client.get("/")
    assert response.status_code == 200


def test_root_contains_welcome_message(client):
    data = client.get("/").json()
    assert "message" in data
    assert "GridPulse" in data["message"]


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_returns_ok_status(client):
    data = client.get("/health").json()
    assert data == {"status": "ok"}
