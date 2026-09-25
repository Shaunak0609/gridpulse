"""
Tests for GET /calendar's teaser/sprint-weekend/circuit-type additions.
Uses the shared `client`/`db` fixtures — no real network calls.
"""

from datetime import date, timedelta

from app.models.driver import Driver
from app.models.race import Race
from app.models.race_result import RaceResult
from app.models.session import Session as RaceSession
from app.models.team import Team
from app.routes import calendar as calendar_module

_TEST_SEASON = 2098  # sandboxed — monkeypatched as the active SEASON per test


def test_calendar_returns_200_and_empty_list_when_no_races(client):
    response = client.get("/calendar")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_calendar_flags_sprint_weekend_and_omits_teaser_for_future_race(client, db, monkeypatch):
    monkeypatch.setattr(calendar_module, "SEASON", _TEST_SEASON)
    race = Race(season=_TEST_SEASON, round=1, name="Future Grand Prix",
                circuit_name="Circuit de Monaco", start_date=date.today() + timedelta(days=30))
    db.add(race)
    db.commit()
    db.refresh(race)

    db.add(RaceSession(race_id=race.id, session_type="sprint", session_name="Sprint"))
    db.add(RaceSession(race_id=race.id, session_type="race", session_name="Race"))
    db.commit()

    response = client.get("/calendar")
    assert response.status_code == 200
    entry = next(r for r in response.json() if r["round"] == 1 and r["season"] == _TEST_SEASON)
    assert entry["is_sprint_weekend"] is True
    assert entry["circuit_type"] == "street"  # Monaco is in the hand-maintained lookup
    assert entry["teaser"] is None  # hasn't happened yet


def test_calendar_builds_podium_teaser_for_past_race_with_synced_results(client, db, monkeypatch):
    monkeypatch.setattr(calendar_module, "SEASON", _TEST_SEASON)
    team = Team(jolpica_ref="ferrari-cal", name="Ferrari", constructor_name="Ferrari")
    db.add(team)
    db.commit()
    db.refresh(team)

    driver = Driver(jolpica_ref="leclerc-cal", code="LEC", full_name="Charles Leclerc",
                     driver_number=16, team_id=team.id)
    db.add(driver)
    db.commit()
    db.refresh(driver)

    race = Race(season=_TEST_SEASON, round=2, name="Past Grand Prix",
                circuit_name="Some New Circuit", start_date=date.today() - timedelta(days=7))
    db.add(race)
    db.commit()
    db.refresh(race)

    session = RaceSession(race_id=race.id, session_type="race", session_name="Race")
    db.add(session)
    db.commit()
    db.refresh(session)

    db.add(RaceResult(session_id=session.id, driver_id=driver.id, team_id=team.id,
                       position=1, status="Finished"))
    db.commit()

    response = client.get("/calendar")
    entry = next(r for r in response.json() if r["round"] == 2 and r["season"] == _TEST_SEASON)
    assert entry["circuit_type"] == "permanent"  # unknown circuit defaults to permanent
    assert entry["teaser"] is not None
    assert entry["teaser"]["podium"][0]["driver_name"] == "Charles Leclerc"
