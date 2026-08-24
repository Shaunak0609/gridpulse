"""
Tests for app.services.data_ingestion.sync_race_results — verifies the
upsert behaviour and that it handles rounds that haven't run yet (Jolpica
returns an empty result list), without making any real network calls.
"""

from app.models.driver import Driver
from app.models.race import Race
from app.models.race_result import RaceResult
from app.models.session import Session as RaceSession
from app.models.team import Team
from app.services import data_ingestion

_TEST_SEASON = 2099  # sandboxed season, never collides with real synced data


def _seed_round(db, round_num: int):
    # Team/driver are shared reference data — reuse across rounds within the
    # same test session instead of re-inserting (jolpica_ref is unique).
    team = db.query(Team).filter_by(jolpica_ref="mclaren").first()
    if not team:
        team = Team(jolpica_ref="mclaren", name="McLaren", constructor_name="McLaren")
        db.add(team)
        db.commit()
        db.refresh(team)

    driver = db.query(Driver).filter_by(jolpica_ref="norris").first()
    if not driver:
        driver = Driver(
            jolpica_ref="norris", code="NOR", full_name="Lando Norris",
            driver_number=4, team_id=team.id,
        )
        db.add(driver)
        db.commit()
        db.refresh(driver)

    race = Race(season=_TEST_SEASON, round=round_num, name="Test Grand Prix")
    db.add(race)
    db.commit()
    db.refresh(race)

    session = RaceSession(race_id=race.id, session_type="race", session_name="Race")
    db.add(session)
    db.commit()
    db.refresh(session)

    return driver, session


def test_sync_race_results_inserts_official_disqualification(db, monkeypatch):
    monkeypatch.setattr(data_ingestion, "SEASON", _TEST_SEASON)
    driver, session = _seed_round(db, round_num=1)

    fake_results = [{
        "position": "18",
        "positionText": "D",
        "status": "Disqualified",
        "grid": "5",
        "points": "0",
        "laps": "57",
        "Driver": {"driverId": "norris"},
        "Constructor": {"constructorId": "mclaren"},
    }]
    monkeypatch.setattr(
        data_ingestion, "fetch_race_results",
        lambda season, round_num: fake_results,
    )

    assert data_ingestion.sync_race_results(db) is True

    result = (
        db.query(RaceResult)
        .filter_by(session_id=session.id, driver_id=driver.id)
        .first()
    )
    assert result is not None
    assert result.status == "Disqualified"
    assert result.position == 18
    assert result.position_text == "D"


def test_sync_race_results_skips_rounds_not_yet_run(db, monkeypatch):
    monkeypatch.setattr(data_ingestion, "SEASON", _TEST_SEASON)
    _seed_round(db, round_num=2)

    # Jolpica returns an empty Results list for rounds that haven't happened.
    monkeypatch.setattr(data_ingestion, "fetch_race_results", lambda season, round_num: [])

    # Should complete successfully — an unraced round is not an error.
    assert data_ingestion.sync_race_results(db) is True
