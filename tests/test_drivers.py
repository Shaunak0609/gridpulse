"""
Tests for GET /drivers and GET /drivers/{id}.

The test database starts empty — no drivers are seeded.
GET /drivers returns an empty list, which is a valid 200 response.
GET /drivers/{id} with any ID returns 404 because the table is empty.
"""


def test_get_drivers_returns_200(client):
    response = client.get("/drivers")
    assert response.status_code == 200


def test_get_drivers_returns_a_list(client):
    data = client.get("/drivers").json()
    assert isinstance(data, list)


def test_get_driver_not_found_returns_404(client):
    # No drivers in the test database, so any ID should be 404.
    response = client.get("/drivers/1")
    assert response.status_code == 404


def test_get_driver_not_found_has_detail_message(client):
    data = client.get("/drivers/999").json()
    assert "detail" in data
    assert "999" in data["detail"]
