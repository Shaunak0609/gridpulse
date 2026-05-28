"""
Shared pytest fixtures for the GridPulse test suite.

HOW THE TEST DATABASE WORKS
────────────────────────────
Tests use an in-memory SQLite database instead of the real PostgreSQL database.
This means:
  • Tests run fast — no network, no disk I/O.
  • The real database is never touched by the test suite.
  • Each pytest session starts with a clean, empty database.

The DATABASE_URL environment variable is forced to SQLite *before* any app
module is imported, so database.py never tries to connect to PostgreSQL.
"""

import os

# TEST_DATABASE_URL lets you point the test suite at a real PostgreSQL database
# (e.g. a dedicated gridpulse_test database) instead of SQLite.
# If it is not set, tests fall back to an in-memory SQLite database.
# Either way, the development database is never touched.
_TEST_DB_URL = os.environ.get("TEST_DATABASE_URL", "sqlite:///:memory:")
os.environ["DATABASE_URL"] = _TEST_DB_URL

# Provide fallbacks for secrets that FastAPI reads at startup.
# In CI there is no .env file; locally these are already set in .env.
os.environ.setdefault("JWT_SECRET_KEY", "test-only-secret-not-for-production")
os.environ.setdefault("JWT_ALGORITHM", "HS256")
os.environ.setdefault("JWT_EXPIRE_MINUTES", "60")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base, get_db
from app.main import app

# StaticPool makes every connection share the same in-memory database.
# Without it, each new connection would get its own empty database.
_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    """Create all SQLAlchemy tables once for the entire test session."""
    Base.metadata.create_all(bind=_engine)
    yield
    Base.metadata.drop_all(bind=_engine)


@pytest.fixture()
def db(_create_tables):
    """
    Yield a database session for one test.
    The session is closed (but not rolled back) after the test finishes.
    Data written in one test persists for later tests in the same session —
    tests that need a clean slate should use unique data (e.g. unique emails).
    """
    session = _TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(db):
    """
    FastAPI TestClient with the real database replaced by the SQLite test DB.

    How dependency override works:
      FastAPI resolves get_db every time a route is called.
      app.dependency_overrides replaces it with a function that returns our
      test session instead, so all database access in tests goes to SQLite.
    """
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    """
    Register and log in a test user, then return the Authorization header dict.

    Usage in a test:
        def test_something(client, auth_headers):
            response = client.get("/users/me", headers=auth_headers)

    The signup call is safe to repeat across tests — if the user already exists
    the 400 is ignored and the login still succeeds with the existing account.
    """
    client.post("/auth/signup", json={
        "email": "fixture-user@example.com",
        "password": "testpassword123",
    })
    resp = client.post("/auth/login", json={
        "email": "fixture-user@example.com",
        "password": "testpassword123",
    })
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
