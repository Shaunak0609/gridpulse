from fastapi import APIRouter

router = APIRouter()

standings = [
    {"position": 1, "driver": "Max Verstappen",  "team": "Red Bull Racing", "points": 77, "wins": 3},
    {"position": 2, "driver": "Lando Norris",    "team": "McLaren",         "points": 62, "wins": 1},
    {"position": 3, "driver": "Charles Leclerc", "team": "Ferrari",         "points": 48, "wins": 0},
    {"position": 4, "driver": "Lewis Hamilton",  "team": "Ferrari",         "points": 35, "wins": 0},
]


@router.get("/standings/drivers")
def get_driver_standings():
    return standings
