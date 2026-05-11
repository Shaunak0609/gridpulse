from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.driver import Driver
from app.schemas.driver import DriverSchema

router = APIRouter()


@router.get("/drivers", response_model=list[DriverSchema])
def get_drivers(db: Session = Depends(get_db)):
    drivers = db.query(Driver).all()
    return [
        {
            "id": d.id,
            "code": d.code,
            "full_name": d.full_name,
            "nationality": d.nationality,
            "driver_number": d.driver_number,
            "team": d.team.name if d.team else None,
        }
        for d in drivers
    ]


@router.get("/drivers/{driver_id}", response_model=DriverSchema)
def get_driver(driver_id: int, db: Session = Depends(get_db)):
    driver = db.query(Driver).filter(Driver.id == driver_id).first()

    if not driver:
        raise HTTPException(status_code=404, detail=f"Driver with id {driver_id} not found")

    return {
        "id": driver.id,
        "code": driver.code,
        "full_name": driver.full_name,
        "nationality": driver.nationality,
        "driver_number": driver.driver_number,
        "team": driver.team.name if driver.team else None,
    }
