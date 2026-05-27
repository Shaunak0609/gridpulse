"""
Tests for signup, login, and the protected GET /users/me endpoint.
"""


# ── Signup ───────────────────────────────────────────────────────────────────

def test_signup_returns_201(client):
    response = client.post("/auth/signup", json={
        "email": "signup-201@example.com",
        "password": "password123",
    })
    assert response.status_code == 201


def test_signup_returns_user_data(client):
    response = client.post("/auth/signup", json={
        "email": "signup-data@example.com",
        "password": "password123",
    })
    data = response.json()
    assert data["email"] == "signup-data@example.com"
    assert "id" in data
    # Password must never appear in the response.
    assert "password" not in data
    assert "password_hash" not in data


def test_signup_duplicate_email_returns_400(client):
    payload = {"email": "duplicate@example.com", "password": "password123"}
    client.post("/auth/signup", json=payload)          # first signup — succeeds
    response = client.post("/auth/signup", json=payload)  # second — must fail
    assert response.status_code == 400


# ── Login ────────────────────────────────────────────────────────────────────

def test_login_returns_access_token(client):
    client.post("/auth/signup", json={
        "email": "login-token@example.com",
        "password": "password123",
    })
    response = client.post("/auth/login", json={
        "email": "login-token@example.com",
        "password": "password123",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password_returns_401(client):
    client.post("/auth/signup", json={
        "email": "login-wrong@example.com",
        "password": "correctpassword",
    })
    response = client.post("/auth/login", json={
        "email": "login-wrong@example.com",
        "password": "wrongpassword",
    })
    assert response.status_code == 401


def test_login_unknown_email_returns_401(client):
    response = client.post("/auth/login", json={
        "email": "nobody@example.com",
        "password": "password123",
    })
    assert response.status_code == 401


# ── Protected route: GET /users/me ───────────────────────────────────────────

def test_get_me_without_token_returns_401(client):
    response = client.get("/users/me")
    assert response.status_code == 401


def test_get_me_with_valid_token_returns_200(client, auth_headers):
    response = client.get("/users/me", headers=auth_headers)
    assert response.status_code == 200


def test_get_me_returns_correct_email(client, auth_headers):
    data = client.get("/users/me", headers=auth_headers).json()
    assert data["email"] == "fixture-user@example.com"


def test_get_me_with_invalid_token_returns_401(client):
    response = client.get("/users/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
