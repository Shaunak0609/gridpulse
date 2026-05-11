from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.race import Race

router = APIRouter()


@router.get("/calendar")
def get_calendar(db: Session = Depends(get_db)):
    races = db.query(Race).order_by(Race.round).all()
    return [
        {
            "id": r.id,
            "season": r.season,
            "round": r.round,
            "name": r.name,
            "circuit_name": r.circuit_name,
            "country": r.country,
            "start_date": str(r.start_date),
        }
        for r in races
    ]
