from fastapi import FastAPI, HTTPException

app = FastAPI(title="GridPulse", description="F1 Race Intelligence Platform")


# --- Sample Data ---

drivers = [
    {"id": 1, "code": "VER", "full_name": "Max Verstappen",  "team": "Red Bull Racing", "nationality": "Dutch",   "number": 1},
    {"id": 2, "code": "NOR", "full_name": "Lando Norris",    "team": "McLaren",         "nationality": "British", "number": 4},
    {"id": 3, "code": "LEC", "full_name": "Charles Leclerc", "team": "Ferrari",         "nationality": "Monégasque", "number": 16},
    {"id": 4, "code": "HAM", "full_name": "Lewis Hamilton",  "team": "Ferrari",         "nationality": "British", "number": 44},
]

teams = [
    {"id": 1, "name": "Red Bull Racing", "base": "Milton Keynes, UK",  "team_principal": "Christian Horner"},
    {"id": 2, "name": "McLaren",         "base": "Woking, UK",         "team_principal": "Andrea Stella"},
    {"id": 3, "name": "Ferrari",         "base": "Maranello, Italy",   "team_principal": "Frederic Vasseur"},
    {"id": 4, "name": "Mercedes",        "base": "Brackley, UK",       "team_principal": "Toto Wolff"},
]

calendar = [
    {"id": 1, "round": 1, "name": "Bahrain Grand Prix",       "circuit": "Bahrain International Circuit", "country": "Bahrain",   "date": "2025-03-02"},
    {"id": 2, "round": 2, "name": "Saudi Arabian Grand Prix", "circuit": "Jeddah Street Circuit",         "country": "Saudi Arabia", "date": "2025-03-09"},
    {"id": 3, "round": 3, "name": "Australian Grand Prix",    "circuit": "Albert Park Circuit",           "country": "Australia", "date": "2025-03-16"},
]

standings = [
    {"position": 1, "driver": "Max Verstappen",  "team": "Red Bull Racing", "points": 77,  "wins": 3},
    {"position": 2, "driver": "Lando Norris",    "team": "McLaren",         "points": 62,  "wins": 1},
    {"position": 3, "driver": "Charles Leclerc", "team": "Ferrari",         "points": 48,  "wins": 0},
    {"position": 4, "driver": "Lewis Hamilton",  "team": "Ferrari",         "points": 35,  "wins": 0},
]


# --- Root & Health ---

@app.get("/")
def root():
    return {"message": "Welcome to GridPulse", "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}


# --- Drivers ---

@app.get("/drivers")
def get_drivers():
    return drivers


@app.get("/drivers/{driver_id}")
def get_driver(driver_id: int):
    for driver in drivers:
        if driver["id"] == driver_id:
            return driver
    raise HTTPException(status_code=404, detail="Driver not found")


# --- Teams ---

@app.get("/teams")
def get_teams():
    return teams


# --- Calendar ---

@app.get("/calendar")
def get_calendar():
    return calendar


# --- Standings ---

@app.get("/standings/drivers")
def get_driver_standings():
    return standings
