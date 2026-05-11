from fastapi import APIRouter, HTTPException

router = APIRouter()

drivers = [
    {"id": 1, "code": "VER", "full_name": "Max Verstappen",  "team": "Red Bull Racing", "nationality": "Dutch",      "number": 1},
    {"id": 2, "code": "NOR", "full_name": "Lando Norris",    "team": "McLaren",         "nationality": "British",    "number": 4},
    {"id": 3, "code": "LEC", "full_name": "Charles Leclerc", "team": "Ferrari",         "nationality": "Monégasque", "number": 16},
    {"id": 4, "code": "HAM", "full_name": "Lewis Hamilton",  "team": "Ferrari",         "nationality": "British",    "number": 44},
]


@router.get("/drivers")
def get_drivers():
    return drivers


@router.get("/drivers/{driver_id}")
def get_driver(driver_id: int):
    for driver in drivers:
        if driver["id"] == driver_id:
            return driver
    raise HTTPException(status_code=404, detail="Driver not found")
