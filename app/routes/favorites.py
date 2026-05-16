from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.models.driver import Driver
from app.models.favorite_driver import FavoriteDriver
from app.models.favorite_team import FavoriteTeam
from app.models.team import Team
from app.models.user import User
from app.schemas.favorite import FavoriteDriverResponse, FavoriteTeamResponse

router = APIRouter(prefix="/me/favorites", tags=["favorites"])


@router.get("/drivers", response_model=list[FavoriteDriverResponse])
def get_favorite_drivers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(FavoriteDriver)
        .filter(FavoriteDriver.user_id == current_user.id)
        .order_by(FavoriteDriver.created_at)
        .all()
    )


@router.post(
    "/drivers/{driver_id}",
    response_model=FavoriteDriverResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_favorite_driver(
    driver_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Driver with id {driver_id} not found.",
        )

    existing = db.query(FavoriteDriver).filter_by(
        user_id=current_user.id,
        driver_id=driver_id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already favourited this driver.",
        )

    favourite = FavoriteDriver(user_id=current_user.id, driver_id=driver_id)
    db.add(favourite)
    db.commit()
    db.refresh(favourite)
    return favourite


@router.delete("/drivers/{driver_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite_driver(
    driver_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    favourite = db.query(FavoriteDriver).filter_by(
        user_id=current_user.id,
        driver_id=driver_id,
    ).first()
    if not favourite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favourite not found.",
        )

    db.delete(favourite)
    db.commit()


# ─── Team favorites ───────────────────────────────────────────────────────────

@router.get("/teams", response_model=list[FavoriteTeamResponse])
def get_favorite_teams(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(FavoriteTeam)
        .filter(FavoriteTeam.user_id == current_user.id)
        .order_by(FavoriteTeam.created_at)
        .all()
    )


@router.post(
    "/teams/{team_id}",
    response_model=FavoriteTeamResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_favorite_team(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Team with id {team_id} not found.",
        )

    existing = db.query(FavoriteTeam).filter_by(
        user_id=current_user.id,
        team_id=team_id,
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You have already favourited this team.",
        )

    favourite = FavoriteTeam(user_id=current_user.id, team_id=team_id)
    db.add(favourite)
    db.commit()
    db.refresh(favourite)
    return favourite


@router.delete("/teams/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_favorite_team(
    team_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    favourite = db.query(FavoriteTeam).filter_by(
        user_id=current_user.id,
        team_id=team_id,
    ).first()
    if not favourite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Favourite not found.",
        )

    db.delete(favourite)
    db.commit()
