from fastapi import FastAPI

app = FastAPI(title="GridPulse", description="F1 Race Intelligence Platform")


@app.get("/")
def root():
    return {"message": "Welcome to GridPulse", "status": "running"}


@app.get("/health")
def health():
    return {"status": "ok"}
