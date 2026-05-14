import os

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.standing import DriverStanding
from app.schemas.standing import DriverStandingSchema

router = APIRouter()

SEASON = int(os.getenv("F1_SEASON", "2026"))


@router.get("/standings/drivers", response_model=list[DriverStandingSchema])
def get_driver_standings(db: Session = Depends(get_db)):
    standings = (
        db.query(DriverStanding)
        .filter(DriverStanding.season == SEASON)
        .order_by(DriverStanding.position)
        .all()
    )
    return [
        {
            "position": s.position,
            "driver": s.driver.full_name,
            "team": s.team.name,
            "points": s.points,
            "wins": s.wins,
            "podiums": s.podiums,
        }
        for s in standings
    ]
