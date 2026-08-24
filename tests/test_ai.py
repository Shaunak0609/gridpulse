"""
Tests for the AI Race Assistant's graceful-degradation behaviour when
OPENAI_API_KEY is not configured. No real OpenAI calls are ever made here —
the test suite never sets OPENAI_API_KEY (see conftest.py), so
ai_service.AI_API_KEY is already empty by default; these tests make that
explicit via monkeypatch and pin the exact behaviour.
"""

from app.services import ai_service


def test_generate_ai_response_without_api_key(monkeypatch):
    monkeypatch.setattr(ai_service, "AI_API_KEY", "")

    text, tokens = ai_service.generate_ai_response("Who won the last race?", "some context")

    assert tokens == 0
    assert "OPENAI_API_KEY" in text


def test_ai_explain_degrades_gracefully_without_api_key(client, auth_headers, monkeypatch):
    monkeypatch.setattr(ai_service, "AI_API_KEY", "")

    response = client.post(
        "/ai/explain",
        json={"prompt": "Who won the last race?"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert "OPENAI_API_KEY" in response.json()["response"]


def test_ai_usage_endpoint_reports_daily_limit(client, auth_headers):
    # Other tests in this session may have already used this fixture user's
    # quota (auth_headers reuses the same account) — assert the invariant,
    # not an exact count, since test order/state isn't guaranteed here.
    response = client.get("/ai/usage", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["daily_limit"] == 20
    assert data["remaining"] == data["daily_limit"] - data["requests_today"]
