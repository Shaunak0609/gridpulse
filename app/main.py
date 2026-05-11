from fastapi import FastAPI

from app.routes import drivers, teams, calendar, standings

app = FastAPI(title="GridPulse", description="F1 Race Intelligence Platform")

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
