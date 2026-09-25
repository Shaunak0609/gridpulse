"""
Tests for GET /drivers and GET /drivers/{id}.

Other test files in this suite seed a handful of Driver rows into the shared
session-scoped SQLite DB (see conftest.py), so "the DB is empty" no longer
holds by the time this file runs — the 404 tests use a high ID that's
guaranteed never to collide with those, rather than assuming emptiness.
"""


def test_get_drivers_returns_200(client):
    response = client.get("/drivers")
    assert response.status_code == 200


def test_get_drivers_returns_a_list(client):
    data = client.get("/drivers").json()
    assert isinstance(data, list)


def test_get_driver_not_found_returns_404(client):
    response = client.get("/drivers/999999")
    assert response.status_code == 404


def test_get_driver_not_found_has_detail_message(client):
    data = client.get("/drivers/999").json()
    assert "detail" in data
    assert "999" in data["detail"]
