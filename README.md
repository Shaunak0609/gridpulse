# GridPulse

**F1 Race Intelligence Platform**

GridPulse is a Formula 1 companion app for fans who want to follow races more intelligently. It provides driver and team information, race calendars, standings, and will eventually support live race data, user accounts, notifications, and AI-powered race analysis.

This repository contains the backend API built with Python and FastAPI.

---

## Current Status — Phase 2

### Phase 1 — Backend Foundations (complete)

- FastAPI application with clean route structure
- PostgreSQL database connection with SQLAlchemy models
- Pydantic schemas for response validation
- Basic error handling and 404 responses

### Phase 2 — Real F1 Data Ingestion (complete)

- Jolpica F1 API client for fetching external data
- Data ingestion service that maps API responses to database models
- Upsert logic — safe to sync multiple times without creating duplicates
- Manual sync script to pull and store real 2025 F1 data
- All 7 endpoints now serve real data from the database

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
| External data | Jolpica F1 API |
| HTTP client | requests |
| Environment | python-dotenv |

---

## External Data Source

**Jolpica F1 API** — `https://api.jolpi.ca/ergast/f1`

Jolpica is a free, public Formula 1 data API. No API key is required. GridPulse uses it to fetch:

| Data | Jolpica endpoint |
|---|---|
| Race calendar | `/2025/races.json` |
| Driver standings | `/2025/driverStandings.json` |
| Constructor standings | `/2025/constructorStandings.json` |

Data is fetched manually and stored in PostgreSQL. The app serves data from its own database, not directly from Jolpica on every request.

**Known limitations of Jolpica data:**
- Team `base` location is not included in the constructor standings endpoint — this field will be `null` until a richer source is added.
- Podium counts are not included in standings — this field is `0` for all drivers.
- Constructor names use Jolpica's short forms, for example `"Red Bull"` instead of `"Red Bull Racing"` and `"Sauber"` instead of `"Kick Sauber"`.

---

## Project Structure

```
gridpulse/
├── app/
│   ├── database/
│   │   └── database.py           # DB engine, session, Base
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
│   ├── services/
│   │   ├── f1_api_client.py      # HTTP client for Jolpica API
│   │   └── data_ingestion.py     # maps API data into SQLAlchemy models
│   └── main.py
├── scripts/
│   ├── create_tables.py          # creates tables in PostgreSQL
│   ├── seed.py                   # inserts small local sample data (Phase 1)
│   └── sync_f1_data.py           # fetches and stores real F1 data from Jolpica
├── .env                          # local environment variables (not committed)
├── .env.example                  # template showing required variables
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

### 7. Sync real F1 data from Jolpica

```bash
python scripts/sync_f1_data.py
```

This fetches real 2025 F1 data from the Jolpica API and stores it in your database. An internet connection is required.

Expected output:

```
=== GridPulse F1 Data Sync — 2025 season ===

[Teams]
  Fetching: https://api.jolpi.ca/ergast/f1/2025/constructorStandings.json
  OK — 10 inserted, 0 updated.

[Drivers]
  Fetching: https://api.jolpi.ca/ergast/f1/2025/driverStandings.json
  OK — 20 inserted, 0 updated, 0 skipped.

[Race Calendar]
  Fetching: https://api.jolpi.ca/ergast/f1/2025/races.json?limit=100
  OK — 24 inserted, 0 updated.

[Driver Standings]
  Fetching: https://api.jolpi.ca/ergast/f1/2025/driverStandings.json
  OK — 20 inserted, 0 updated, 0 skipped.

=== Sync Summary ===
  Teams                OK
  Drivers              OK
  Race Calendar        OK
  Driver Standings     OK

All steps completed successfully.
```

This script is safe to run multiple times. Re-running it updates existing rows rather than creating duplicates.

### 8. Run the development server

```bash
uvicorn app.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`.

`--reload` restarts the server automatically when you save changes to a file. Use this during development only.

---

## Verifying Synced Data in PostgreSQL

Connect to psql after running the sync:

```bash
psql postgresql://your_username:yourpassword@localhost:5432/gridpulse_db
```

Check row counts:

```sql
SELECT COUNT(*) FROM teams;           -- 10
SELECT COUNT(*) FROM drivers;         -- 20
SELECT COUNT(*) FROM races;           -- 24
SELECT COUNT(*) FROM driver_standings; -- 20
```

Check drivers with their team names:

```sql
SELECT d.full_name, d.code, t.name AS team
FROM drivers d
JOIN teams t ON d.team_id = t.id
ORDER BY d.full_name;
```

Check the race calendar:

```sql
SELECT round, name, country, start_date
FROM races
ORDER BY round;
```

Check driver standings:

```sql
SELECT s.position, d.full_name, t.name AS team, s.points, s.wins
FROM driver_standings s
JOIN drivers d ON s.driver_id = d.id
JOIN teams t ON s.team_id = t.id
ORDER BY s.position;
```

---

## Available Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Welcome message |
| GET | `/health` | Health check |
| GET | `/drivers` | List all 20 drivers |
| GET | `/drivers/{id}` | Get a single driver by ID |
| GET | `/teams` | List all 10 teams |
| GET | `/calendar` | Full 2025 race calendar |
| GET | `/standings/drivers` | Driver championship standings |

---

## Example Responses

### `GET /drivers`

```json
[
  {
    "id": 1,
    "code": "NOR",
    "full_name": "Lando Norris",
    "nationality": "British",
    "driver_number": 4,
    "team": "McLaren"
  },
  {
    "id": 2,
    "code": "VER",
    "full_name": "Max Verstappen",
    "nationality": "Dutch",
    "driver_number": 1,
    "team": "Red Bull"
  }
]
```

### `GET /drivers/1`

```json
{
  "id": 1,
  "code": "NOR",
  "full_name": "Lando Norris",
  "nationality": "British",
  "driver_number": 4,
  "team": "McLaren"
}
```

### `GET /drivers/999` — driver not found

```json
{
  "detail": "Driver with id 999 not found"
}
```

HTTP status: `404 Not Found`

### `GET /teams`

```json
[
  {
    "id": 1,
    "name": "McLaren",
    "constructor_name": "McLaren",
    "base": null
  },
  {
    "id": 2,
    "name": "Red Bull",
    "constructor_name": "Red Bull",
    "base": null
  }
]
```

Note: `base` is `null` — the Jolpica constructor standings endpoint does not include team base location.

### `GET /calendar`

```json
[
  {
    "id": 1,
    "season": 2025,
    "round": 1,
    "name": "Australian Grand Prix",
    "circuit_name": "Albert Park Grand Prix Circuit",
    "country": "Australia",
    "start_date": "2025-03-16"
  }
]
```

### `GET /standings/drivers`

```json
[
  {
    "position": 1,
    "driver": "Lando Norris",
    "team": "McLaren",
    "points": 151.0,
    "wins": 4,
    "podiums": 0
  },
  {
    "position": 2,
    "driver": "Max Verstappen",
    "team": "Red Bull",
    "points": 136.0,
    "wins": 3,
    "podiums": 0
  }
]
```

Note: `podiums` is `0` for all drivers — Jolpica standings do not include podium counts.

---

## Interactive API Docs

FastAPI generates interactive documentation automatically.

Open `http://127.0.0.1:8000/docs` in your browser while the server is running. You can browse every endpoint, see the expected response shape, and test requests directly from the browser without any extra tools.

---

## What Is Not Included Yet

The following features are planned but not yet built:

- Frontend of any kind
- User accounts or authentication
- Google sign-in
- Favourite drivers or teams
- Notifications of any kind
- Email notifications
- Race calendar reminders
- AI features
- Live race data
- Race control messages
- Tyre/pit stop data
- Track map
- Strategy analytics
- WebSockets
- Redis
- Docker
- OpenF1 or FastF1 integration
- ML predictions
- Scheduled or automatic data sync
- Constructor standings endpoint
- Team base location data

---

## Future Phases

**Phase 3 — Frontend Foundation + Multi-Page UI**
Build a React frontend with Tailwind CSS and React Router. Pages: Home, Drivers, Driver Detail, Teams, Calendar, Standings. Consumes the existing public API endpoints.

**Phase 4 — User Accounts and Local Authentication**
Add email and password authentication with JWT tokens. Users can sign up, log in, and access protected routes.

**Phase 5 — Google Sign-In**
Allow users to sign in with their Google account using OAuth.

**Phase 6 — Race Calendar and In-App Reminders**
Let signed-in users set reminders for upcoming sessions. Background jobs deliver in-app notifications.

**Phase 7 — Email Notifications**
Send optional email reminders for race sessions and favourite-driver updates using a provider such as Resend or SendGrid.

**Phase 8 — Favourite Driver Notifications**
Users can favourite a driver and receive personalised alerts for qualifying results, race results, positions gained or lost, and pit stops.

**Phase 9 — AI Race Assistant**
A protected AI feature for signed-in users. Ask questions about races, drivers, and strategy grounded in real race data.

**Phase 10 — Live Race Dashboard**
A second-screen race dashboard showing the live leaderboard, positions, pit status, tyre compounds, laps remaining, and race control messages.

**Phase 11 — Track Map Visualisation**
A circuit map showing driver positions moving around the track in real time or historical replay.

**Phase 12 — Advanced Analytics**
Tyre strategy visualiser, pit stop comparison, pace charts, driver and team comparisons, and sector analysis.

**Phase 13 — ML Prediction Layer**
Machine learning models for podium prediction, pit window estimation, and race outcome simulation.

---

## Development Notes

- The `.env` file is gitignored and will never be committed. Never hardcode credentials in source files.
- `scripts/create_tables.py` is safe to re-run. It skips tables that already exist.
- `scripts/sync_f1_data.py` is safe to re-run multiple times. It uses upsert logic and will not create duplicate rows.
- `scripts/seed.py` inserts a small hardcoded dataset used during Phase 1 development. It is no longer needed now that `sync_f1_data.py` exists.
- There is no Alembic migration system yet. For model changes, drop the affected tables manually and recreate them with `create_tables.py`.
- Data sync is manual. There is no scheduled or automatic sync yet.
