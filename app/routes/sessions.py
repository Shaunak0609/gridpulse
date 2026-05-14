import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.race import Race
from app.models.session import Session as RaceSession
from app.schemas.session import SessionResponse

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
