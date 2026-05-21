import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_optional_user
from app.database.database import get_db
from app.models.lap import Lap
from app.models.race import Race
from app.models.race_control_message import RaceControlMessage
from app.models.session import Session as RaceSession
from app.models.stint import Stint
from app.models.user import User
from app.models.weather_sample import WeatherSample
from app.schemas.lap import LapResponse
from app.schemas.race_control_message import RaceControlMessageResponse
from app.schemas.session import SessionDetailResponse, SessionResponse
from app.schemas.session_dashboard import SessionDashboardResponse
from app.schemas.strategy_dashboard import StrategyDashboardResponse
from app.schemas.stint import StintResponse
from app.schemas.weather_sample import WeatherSampleResponse
from app.services.session_dashboard import get_session_summary
from app.services.strategy_dashboard import get_strategy_summary

router = APIRouter(tags=["sessions"])

SEASON = int(os.getenv("F1_SEASON", "2026"))


@router.get("/sessions/upcoming", response_model=list[SessionResponse])
def get_upcoming_sessions(
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    sessions = (
        db.query(RaceSession)
        .join(Race)
        .filter(
            Race.season == SEASON,
            RaceSession.start_time != None,   # noqa: E711
            RaceSession.start_time >= now,
        )
        .order_by(RaceSession.start_time)
        .limit(limit)
        .all()
    )
    return sessions


@router.get("/races/{race_id}/sessions", response_model=list[SessionResponse])
def get_sessions_for_race(race_id: int, db: Session = Depends(get_db)):
    race = db.query(Race).filter(Race.id == race_id).first()
    if not race:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Race with id {race_id} not found.",
        )

    sessions = (
        db.query(RaceSession)
        .filter(RaceSession.race_id == race_id)
        .order_by(RaceSession.start_time)
        .all()
    )
    return sessions


# ─── Synced sessions list ────────────────────────────────────────────────────

@router.get("/sessions/synced", response_model=list[SessionDetailResponse])
def get_synced_sessions(db: Session = Depends(get_db)):
    """
    Return all sessions that have been synced from OpenF1
    (i.e. openf1_session_key is set), ordered most-recent first.

    Used by the Race Dashboard session picker on the frontend.
    """
    sessions = (
        db.query(RaceSession)
        .filter(RaceSession.openf1_session_key.isnot(None))
        .order_by(RaceSession.start_time.desc())
        .all()
    )
    # SessionDetailResponse needs race_name — build the list explicitly
    result = []
    for s in sessions:
        result.append({
            "id": s.id,
            "race_id": s.race_id,
            "session_type": s.session_type,
            "session_name": s.session_name,
            "start_time": s.start_time,
            "end_time": s.end_time,
            "timezone": s.timezone,
            "circuit_short_name": s.circuit_short_name,
            "country_name": s.country_name,
            "openf1_session_key": s.openf1_session_key,
            "race_name": s.race.name if s.race else None,
        })
    return result


# ─── Single session lookup ───────────────────────────────────────────────────

@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
def get_session(session_id: int, db: Session = Depends(get_db)):
    """Fetch a single session with race name and OpenF1 link metadata."""
    local = (
        db.query(RaceSession).filter(RaceSession.id == session_id).first()
    )
    if not local:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found.",
        )
    race = db.query(Race).filter(Race.id == local.race_id).first()
    return {
        "id": local.id,
        "race_id": local.race_id,
        "session_type": local.session_type,
        "session_name": local.session_name,
        "start_time": local.start_time,
        "end_time": local.end_time,
        "timezone": local.timezone,
        "circuit_short_name": local.circuit_short_name,
        "country_name": local.country_name,
        "openf1_session_key": local.openf1_session_key,
        "race_name": race.name if race else None,
    }


# ─── Historical data helpers ──────────────────────────────────────────────────

def _get_session_or_404(session_id: int, db: Session) -> RaceSession:
    """Return the local session row, or raise 404."""
    session = db.query(RaceSession).filter(RaceSession.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found.",
        )
    return session


# ─── Historical data endpoints ────────────────────────────────────────────────

@router.get("/sessions/{session_id}/dashboard", response_model=SessionDashboardResponse)
def get_session_dashboard(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """
    Return a structured dashboard summary for one session.

    Public endpoint — no token required.
    If a valid Bearer token is provided, the response marks favourite
    drivers with is_favourite=True in the finishing order and stint summary.

    Returns 404 if the session does not exist.
    Returns the full schema with has_* flags set to False for every section
    that has no historical data (session not synced or data not ingested).
    """
    summary = get_session_summary(session_id, db, current_user)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found.",
        )
    return SessionDashboardResponse.from_summary(summary)


@router.get("/sessions/{session_id}/strategy", response_model=StrategyDashboardResponse)
def get_session_strategy(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """
    Return a strategy summary for one session.

    Public endpoint — no token required.
    If a valid Bearer token is provided, the response marks favourite
    drivers with is_favourite=True in driver_strategies.

    Returns 404 if the session does not exist.
    Returns the full schema with has_stint_data=False (and empty strategy
    sections) when the session has not been synced or has no tyre data.
    """
    summary = get_strategy_summary(session_id, db, current_user)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found.",
        )
    return StrategyDashboardResponse.from_summary(summary)


@router.get("/sessions/{session_id}/laps", response_model=list[LapResponse])
def get_laps(session_id: int, db: Session = Depends(get_db)):
    """All laps for a session, ordered by driver number then lap number."""
    _get_session_or_404(session_id, db)
    return (
        db.query(Lap)
        .filter(Lap.session_id == session_id)
        .order_by(Lap.driver_number, Lap.lap_number)
        .all()
    )


@router.get("/sessions/{session_id}/stints", response_model=list[StintResponse])
def get_stints(session_id: int, db: Session = Depends(get_db)):
    """All stints for a session, ordered by driver number then stint start lap."""
    _get_session_or_404(session_id, db)
    return (
        db.query(Stint)
        .filter(Stint.session_id == session_id)
        .order_by(Stint.driver_number, Stint.lap_start)
        .all()
    )


@router.get("/sessions/{session_id}/race-control", response_model=list[RaceControlMessageResponse])
def get_race_control(session_id: int, db: Session = Depends(get_db)):
    """All race control messages for a session, ordered by timestamp."""
    _get_session_or_404(session_id, db)
    return (
        db.query(RaceControlMessage)
        .filter(RaceControlMessage.session_id == session_id)
        .order_by(RaceControlMessage.date)
        .all()
    )


@router.get("/sessions/{session_id}/weather", response_model=list[WeatherSampleResponse])
def get_weather(session_id: int, db: Session = Depends(get_db)):
    """All weather samples for a session, ordered by timestamp."""
    _get_session_or_404(session_id, db)
    return (
        db.query(WeatherSample)
        .filter(WeatherSample.session_id == session_id)
        .order_by(WeatherSample.date)
        .all()
    )
