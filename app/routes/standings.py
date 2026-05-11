from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.standing import DriverStanding

router = APIRouter()


@router.get("/standings/drivers")
def get_driver_standings(db: Session = Depends(get_db)):
    standings = db.query(DriverStanding).order_by(DriverStanding.position).all()
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
