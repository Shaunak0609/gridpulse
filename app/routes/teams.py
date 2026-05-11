from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.team import Team
from app.schemas.team import TeamSchema

router = APIRouter()


@router.get("/teams", response_model=list[TeamSchema])
def get_teams(db: Session = Depends(get_db)):
    teams = db.query(Team).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "constructor_name": t.constructor_name,
            "base": t.base,
        }
        for t in teams
    ]
