from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import drivers, teams, calendar, standings, auth, users

app = FastAPI(title="GridPulse", description="F1 Race Intelligence Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(drivers.router)
app.include_router(teams.router)
app.include_router(calendar.router)
app.include_router(standings.router)


@app.get("/")
def root():
    return {"message": "Welcome to GridPulse", "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}
