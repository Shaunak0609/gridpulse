from fastapi import APIRouter

router = APIRouter()

teams = [
    {"id": 1, "name": "Red Bull Racing", "base": "Milton Keynes, UK", "team_principal": "Christian Horner"},
    {"id": 2, "name": "McLaren",         "base": "Woking, UK",        "team_principal": "Andrea Stella"},
    {"id": 3, "name": "Ferrari",         "base": "Maranello, Italy",  "team_principal": "Frederic Vasseur"},
    {"id": 4, "name": "Mercedes",        "base": "Brackley, UK",      "team_principal": "Toto Wolff"},
]


@router.get("/teams")
def get_teams():
    return teams
