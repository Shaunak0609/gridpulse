from fastapi import APIRouter

router = APIRouter()

calendar = [
    {"id": 1, "round": 1, "name": "Bahrain Grand Prix",       "circuit": "Bahrain International Circuit", "country": "Bahrain",      "date": "2025-03-02"},
    {"id": 2, "round": 2, "name": "Saudi Arabian Grand Prix", "circuit": "Jeddah Street Circuit",         "country": "Saudi Arabia", "date": "2025-03-09"},
    {"id": 3, "round": 3, "name": "Australian Grand Prix",    "circuit": "Albert Park Circuit",           "country": "Australia",    "date": "2025-03-16"},
]


@router.get("/calendar")
def get_calendar():
    return calendar
