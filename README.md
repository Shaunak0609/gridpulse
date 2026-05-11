# GridPulse

**F1 Race Intelligence Platform**

GridPulse is a Formula 1 companion app for fans who want to follow races more intelligently. It provides driver and team information, race calendars, standings, and will eventually support live race data, user accounts, notifications, and AI-powered race analysis.

This repository contains the backend API built with Python and FastAPI.

---

## Current Status — Phase 1

Phase 1 is a working REST API backend with:

- FastAPI application with clean route structure
- PostgreSQL database with SQLAlchemy models
- Seeded 2025 F1 data (drivers, teams, calendar, standings)
- 7 endpoints returning real data from the database
- Pydantic schemas for response validation

There is no frontend yet. All features are tested via the browser, curl, or the built-in API docs at `/docs`.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.11+ |
| Web framework | FastAPI |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Data validation | Pydantic |
| Server | Uvicorn |
| Environment | python-dotenv |

---

## Project Structure

```
gridpulse/
├── app/
│   ├── database/
│   │   └── database.py       # DB engine, session, Base
│   ├── models/
│   │   ├── team.py
│   │   ├── driver.py
│   │   ├── race.py
│   │   └── standing.py
│   ├── schemas/
│   │   ├── team.py
│   │   ├── driver.py
│   │   ├── race.py
│   │   └── standing.py
│   ├── routes/
│   │   ├── drivers.py
│   │   ├── teams.py
│   │   ├── calendar.py
│   │   └── standings.py
│   └── main.py
├── scripts/
│   ├── create_tables.py      # creates tables in PostgreSQL
│   └── seed.py               # inserts sample F1 data
├── .env                      # local environment variables (not committed)
├── .env.example              # template showing required variables
└── requirements.txt
```

---

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/your-username/gridpulse.git
cd gridpulse
```

### 2. Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate
```

You should see `(venv)` appear in your terminal prompt. Run this activation command each time you open a new terminal session.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Set up PostgreSQL

Make sure PostgreSQL is installed and running. If you used Homebrew on Mac:

```bash
brew services start postgresql@14
```

Create the database:

```bash
psql postgres
```

Inside the psql prompt:

```sql
CREATE DATABASE gridpulse_db;
\q
```

### 5. Create your `.env` file

Copy the example file:

```bash
cp .env.example .env
```

Open `.env` and fill in your database credentials:

```
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/gridpulse_db
```

Replace `your_username` and `your_password` with your actual PostgreSQL credentials. Your username is usually your Mac username — run `whoami` in the terminal if you are unsure.

### 6. Create the database tables

```bash
python scripts/create_tables.py
```

Expected output:

```
Creating tables...
Done. Tables created:
  - teams
  - drivers
  - races
  - driver_standings
```

### 7. Seed the database

```bash
python scripts/seed.py
```

Expected output:

```
Seeding teams...
Seeding drivers...
Seeding races...
Seeding driver standings...
Seed complete.
```

This script is safe to run multiple times. It skips seeding if data already exists.

### 8. Run the development server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

`--reload` restarts the server automatically when you save changes to a file. Use this during development only.

---

## Available Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Welcome message |
| GET | `/health` | Health check |
| GET | `/drivers` | List all drivers |
| GET | `/drivers/{id}` | Get a single driver by ID |
| GET | `/teams` | List all teams |
| GET | `/calendar` | List all races in the season |
| GET | `/standings/drivers` | Driver championship standings |

---

## Example Responses

### `GET /`

```json
{
  "message": "Welcome to GridPulse",
  "status": "running"
}
```

### `GET /health`

```json
{
  "status": "ok"
}
```

### `GET /drivers`

```json
[
  {
    "id": 1,
    "code": "VER",
    "full_name": "Max Verstappen",
    "nationality": "Dutch",
    "driver_number": 1,
    "team": "Red Bull Racing"
  },
  {
    "id": 2,
    "code": "NOR",
    "full_name": "Lando Norris",
    "nationality": "British",
    "driver_number": 4,
    "team": "McLaren"
  }
]
```

### `GET /drivers/1`

```json
{
  "id": 1,
  "code": "VER",
  "full_name": "Max Verstappen",
  "nationality": "Dutch",
  "driver_number": 1,
  "team": "Red Bull Racing"
}
```

### `GET /drivers/99` — driver not found

```json
{
  "detail": "Driver with id 99 not found"
}
```

HTTP status: `404 Not Found`

### `GET /teams`

```json
[
  {
    "id": 1,
    "name": "Red Bull Racing",
    "constructor_name": "Red Bull Racing",
    "base": "Milton Keynes, UK"
  },
  {
    "id": 2,
    "name": "McLaren",
    "constructor_name": "McLaren",
    "base": "Woking, UK"
  }
]
```

### `GET /calendar`

```json
[
  {
    "id": 1,
    "season": 2025,
    "round": 1,
    "name": "Bahrain Grand Prix",
    "circuit_name": "Bahrain International Circuit",
    "country": "Bahrain",
    "start_date": "2025-03-02"
  },
  {
    "id": 2,
    "season": 2025,
    "round": 2,
    "name": "Saudi Arabian Grand Prix",
    "circuit_name": "Jeddah Street Circuit",
    "country": "Saudi Arabia",
    "start_date": "2025-03-09"
  }
]
```

### `GET /standings/drivers`

```json
[
  {
    "position": 1,
    "driver": "Max Verstappen",
    "team": "Red Bull Racing",
    "points": 77.0,
    "wins": 3,
    "podiums": 3
  },
  {
    "position": 2,
    "driver": "Lando Norris",
    "team": "McLaren",
    "points": 62.0,
    "wins": 1,
    "podiums": 2
  }
]
```

---

## Interactive API Docs

FastAPI generates interactive documentation automatically.

Open `http://127.0.0.1:8000/docs` in your browser while the server is running. You can browse every endpoint, see the expected response shape, and test requests directly from the browser without any extra tools.

---

## Future Phases

The following features are planned but not yet built.

**Phase 2 — Real F1 Data**
Replace seeded sample data with live data from the Jolpica F1 API. Sync the full 2025 calendar, driver standings, and constructor standings automatically.

**Phase 3 — User Accounts**
Add email and password authentication. Users will be able to sign up, log in, and receive a JWT token for accessing protected routes.

**Phase 4 — Google Sign-In**
Allow users to sign in with their Google account using OAuth.

**Phase 5 — Race Calendar Reminders**
Let signed-in users set reminders for upcoming sessions. Background jobs will send in-app notifications before practice, qualifying, and races.

**Phase 6 — Email Notifications**
Send optional email reminders for race sessions and favourite-driver updates using a provider such as Resend or SendGrid.

**Phase 7 — Favourite Driver Notifications**
Users can favourite a driver. They will receive personalised alerts when their driver qualifies, finishes, gains positions, pits, or receives a penalty.

**Phase 8 — AI Race Assistant**
A protected AI feature for signed-in users. Ask questions about races, drivers, and strategy. The AI will explain what happened and why, grounded in real race data.

**Phase 9 — Live Race Dashboard**
A second-screen race dashboard showing the live leaderboard, current positions, pit status, tyre compounds, laps remaining, and race control messages.

**Phase 10 — Track Map**
A circuit visualisation showing driver positions moving around the track in real time or historical replay.

**Phase 11 — Strategy and Analytics**
Tyre strategy visualiser, pit stop comparison, pace charts, driver and team comparisons, and sector analysis.

**Phase 12 — ML Predictions**
Machine learning models for podium prediction, pit window estimation, and race outcome simulation.

---

## Development Notes

- The `.env` file is gitignored and will never be committed. Never hardcode credentials in source files.
- `scripts/create_tables.py` is safe to re-run. It skips tables that already exist.
- `scripts/seed.py` is safe to re-run. It skips seeding if data already exists.
- There is no Alembic migration system yet. For schema changes in Phase 1, drop and recreate the tables manually.
