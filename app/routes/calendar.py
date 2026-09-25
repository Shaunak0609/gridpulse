import os
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.race import Race
from app.models.race_result import RaceResult
from app.models.session import Session as RaceSession
from app.schemas.race import PodiumEntry, RaceSchema, RaceTeaser
from app.services.analytics_service import build_session_analytics

router = APIRouter()

SEASON = int(os.getenv("F1_SEASON", "2026"))

# Circuit classification — not available from Jolpica or OpenF1, so this is a
# small hand-maintained lookup keyed on the exact circuit_name Jolpica returns.
# Anything not listed defaults to "permanent". Update when the calendar adds
# a new circuit.
CIRCUIT_TYPES: dict[str, str] = {
    "Albert Park Grand Prix Circuit": "street",
    "Miami International Autodrome": "street",
    "Circuit Gilles Villeneuve": "street",
    "Circuit de Monaco": "street",
    "Madring": "street",
    "Baku City Circuit": "street",
    "Marina Bay Street Circuit": "street",
    "Las Vegas Strip Street Circuit": "street",
}


def _build_teaser(race_session: RaceSession | None, db: Session) -> RaceTeaser | None:
    """
    Quick result strip for a finished race: official podium (if results have
    been synced) plus fastest lap (if OpenF1 lap data has been synced).
    Returns None if neither is available yet — not an error, just not synced.
    """
    if not race_session:
        return None

    podium: list[PodiumEntry] = []
    results = (
        db.query(RaceResult)
        .filter(RaceResult.session_id == race_session.id)
        .filter(RaceResult.position.isnot(None))
        .order_by(RaceResult.position)
        .limit(3)
        .all()
    )
    for r in results:
        if not r.driver:
            continue
        podium.append(PodiumEntry(
            position=r.position,
            driver_name=r.driver.full_name,
            team_name=r.team.name if r.team else None,
        ))

    fastest_driver = None
    fastest_lap = None
    if race_session.openf1_session_key:
        try:
            analytics = build_session_analytics(race_session, db)
            fastest_driver = analytics.session_fastest_driver
            fastest_lap = analytics.session_fastest_lap
        except Exception:
            pass  # teaser is a nice-to-have — never break the calendar over it

    if not podium and fastest_driver is None:
        return None

    return RaceTeaser(
        podium=podium,
        fastest_lap_driver=fastest_driver,
        fastest_lap_time=fastest_lap,
    )


@router.get("/calendar", response_model=list[RaceSchema])
def get_calendar(db: Session = Depends(get_db)):
    races = db.query(Race).filter(Race.season == SEASON).order_by(Race.round).all()
    today = date.today()

    result = []
    for r in races:
        sessions = db.query(RaceSession).filter(RaceSession.race_id == r.id).all()
        is_sprint = any(s.session_type == "sprint" for s in sessions)
        race_session = next((s for s in sessions if s.session_type == "race"), None)

        is_past = r.start_date is not None and r.start_date < today
        teaser = _build_teaser(race_session, db) if is_past else None

        result.append({
            "id": r.id,
            "season": r.season,
            "round": r.round,
            "name": r.name,
            "circuit_name": r.circuit_name,
            "country": r.country,
            "start_date": str(r.start_date),
            "is_sprint_weekend": is_sprint,
            "circuit_type": CIRCUIT_TYPES.get(r.circuit_name or "", "permanent"),
            "teaser": teaser,
        })

    return result
