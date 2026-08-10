# GridPulse

**An F1 race intelligence platform for fans who want to follow the sport more closely.**

GridPulse pulls real Formula 1 data — drivers, teams, the race calendar, standings, and historical session detail — into a single companion app with user accounts, reminders, notifications, favourites, historical race dashboards, and an AI race assistant grounded in the app's own data.

🔗 **Live app:** https://gridpulse-mu.vercel.app/

---

## What this project demonstrates

- **Full-stack development** — a FastAPI + PostgreSQL backend and a React + TypeScript frontend, built and deployed end to end.
- **Third-party API integration** — ingests and reconciles data from two public F1 APIs (Jolpica and OpenF1) into a normalised relational schema.
- **Authentication** — email/password and Google OAuth, both issuing JWTs, with account linking.
- **AI integration** — a race assistant grounded in database context with strict anti-hallucination rules, pluggable across providers (Groq / Anthropic).
- **Production concerns** — Docker, an automated test suite, GitHub Actions CI, and a scheduled post-race data sync job.

---

## Features

- 🏎️ **F1 data** — drivers, teams, the season race calendar, and championship standings
- 👤 **Accounts** — email/password and Google sign-in (JWT auth)
- 🔔 **Reminders & notifications** — set reminders for races and sessions, delivered in-app and by email
- ⭐ **Favourites & dashboard** — favourite drivers and teams, with a personalised dashboard
- 🤖 **AI race assistant** — ask questions answered from GridPulse's own data, never invented
- 📊 **Historical dashboards** — per-session Race, Strategy, and Analytics views built from OpenF1 data (laps, stints, tyre strategy, race control, weather)
- 🔄 **Automated data sync** — an idempotent job that refreshes standings and ingests completed race-weekend results

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11+, FastAPI, Uvicorn |
| Database | PostgreSQL, SQLAlchemy, Pydantic |
| Auth | JWT (python-jose), passlib + bcrypt, Google OAuth |
| Frontend | React, Vite, TypeScript, Tailwind CSS v4, React Router, Recharts |
| AI | Groq (default, free tier) or Anthropic |
| Email | Resend |
| Data sources | Jolpica F1 API, OpenF1 API |
| Tooling | Docker, pytest, GitHub Actions |

---

## Architecture

```
React + TypeScript (Vercel)
        │  REST / JWT
        ▼
FastAPI backend (Render)
        │
        ├── PostgreSQL  ← app's own datastore
        ├── Jolpica API ← drivers, teams, calendar, standings
        ├── OpenF1 API  ← historical laps, stints, race control, weather
        └── AI provider ← Groq / Anthropic (grounded in DB context)
```

The frontend never calls external F1 APIs directly. Data is ingested by sync scripts, stored in PostgreSQL, and served from the app's own database — so pages stay fast and the app controls its data.

**Data sources**
- **Jolpica** (`api.jolpi.ca`) — free, no key. Race calendar, driver and constructor standings.
- **OpenF1** (`api.openf1.org`) — free, no key. Historical session detail from 2023 onward (laps, stints, race control, weather). No car telemetry — that would require FastF1, noted as future work.

---

## Project structure

```
gridpulse/
├── app/
│   ├── auth/         # JWT, password hashing, Google OAuth, route dependencies
│   ├── database/     # SQLAlchemy engine, session, Base
│   ├── models/       # SQLAlchemy models (users, drivers, teams, races, sessions, laps, …)
│   ├── schemas/      # Pydantic request/response models
│   ├── routes/       # FastAPI routers (auth, drivers, sessions, ai, analytics, …)
│   ├── services/     # Business logic: data ingestion, AI, dashboards, email, alerts
│   └── main.py       # App entrypoint, CORS, router registration
├── frontend/         # React + Vite + TypeScript app
├── scripts/
│   ├── create_tables.py             # create all tables (idempotent)
│   ├── sync_f1_data.py              # sync Jolpica data + generate driver notifications
│   ├── sync_openf1_session.py       # sync historical OpenF1 session data
│   ├── send_due_reminder_emails.py  # send due reminder emails
│   ├── generate_favorite_driver_alerts.py  # generate session alerts for favourited drivers
│   └── post_race_weekend_sync.py    # idempotent post-race-weekend sync (standings + results)
├── tests/            # pytest suite (SQLite in-memory)
├── docs/             # ENVIRONMENT.md, DEPLOYMENT.md
└── requirements.txt
```

---

## Getting started

### Prerequisites
Docker Desktop (recommended path), or Python 3.11+ / Node 18+ / a local PostgreSQL instance (manual path).

### Option A — Docker Compose (recommended)

Runs Postgres, the FastAPI backend, and the frontend together in containers.

```bash
git clone <repo-url> gridpulse && cd gridpulse
cp .env.example .env             # fill in the values (see below) — DATABASE_URL
                                  # and FRONTEND_URL are overridden automatically
                                  # for the containers, so you don't need to edit those two

open -a Docker                   # make sure Docker Desktop is running first (macOS)

docker compose up --build -d     # builds and starts db + backend + frontend
```

The Postgres container starts with an **empty** database on first run, so create the tables and seed F1 data inside the backend container once the stack is up:

```bash
docker compose exec backend python scripts/create_tables.py
docker compose exec backend python scripts/sync_f1_data.py   # populates drivers, teams, calendar, standings
```

Then open:
- Frontend — http://localhost:3000
- Backend API docs — http://localhost:8000/docs

Useful commands:

```bash
docker compose logs -f       # tail all service logs
docker compose ps            # check container health/status
docker compose down          # stop everything (keeps the Postgres volume)
docker compose down -v       # stop and wipe the Postgres volume
```

To run one-off scripts (e.g. the [post-race-weekend sync](#automated-post-race-weekend-sync)) against the Dockerized database, run them the same way: `docker compose exec backend python scripts/<script>.py`.

### Option B — Run locally without Docker

```bash
git clone <repo-url> gridpulse && cd gridpulse
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # then fill in the values (see below)
python scripts/create_tables.py
python scripts/sync_f1_data.py   # populate drivers, teams, calendar, standings

uvicorn app.main:app --reload    # http://127.0.0.1:8000  (docs at /docs)
```

Minimum `.env` to boot the API:

```
DATABASE_URL=postgresql://user:pass@localhost:5432/gridpulse_db
JWT_SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))">
FRONTEND_URL=http://localhost:5173
F1_SEASON=2026
```

Google sign-in, email (Resend), and the AI assistant each need a few more variables — all documented in [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md).

In a second terminal, start the frontend:

```bash
cd frontend
npm install
npm run dev                      # http://localhost:5173
```

Set `VITE_API_URL` to your backend URL (defaults to local).

This requires a Postgres instance already running and reachable at `DATABASE_URL` — e.g. via `brew services start postgresql@14` on macOS. Note: Option A and Option B both default to Postgres port 5432, so only run one at a time.

---

## API overview

The API is fully documented and explorable at **`/docs`** (Swagger UI) when the backend is running. At a glance:

| Area | Examples |
|---|---|
| Reference data | `GET /drivers`, `GET /teams`, `GET /calendar`, `GET /standings` |
| Auth | `POST /auth/signup`, `POST /auth/login`, `GET /auth/google/start`, `GET /users/me` |
| Reminders & notifications | `GET/POST/DELETE /reminders`, `GET /notifications` |
| Favourites & dashboard | `GET/POST/DELETE /me/favorites/...`, `GET /me/dashboard` |
| Sessions & historical | `GET /sessions/{id}/dashboard`, `/strategy`, `GET /analytics/sessions/{id}` |
| AI assistant | `POST /ai/explain`, `GET /ai/history`, `GET /ai/usage` |

Protected endpoints require a JWT `Bearer` token.

---

## Automated post-race-weekend sync

`scripts/post_race_weekend_sync.py` keeps deployed data current after each race weekend. It:

1. Refreshes teams, drivers, calendar, session schedule, and standings from Jolpica.
2. Detects race weekends whose race day has passed and ingests OpenF1 results (laps, stints, weather, race control) for finished, not-yet-synced sessions.

It's **idempotent and non-destructive** — upserts only, skips already-synced sessions, and never touches user data — so it's safe to run on a schedule (e.g. a weekly Render Cron Job).

```bash
python scripts/post_race_weekend_sync.py               # sync the current season
python scripts/post_race_weekend_sync.py --with-alerts # also generate favourite-driver alerts
```

See [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the cron setup.

---

## Testing & CI

```bash
python -m pytest        # backend tests (SQLite in-memory — never touches your DB)
cd frontend && npm run build && npm run lint
```

GitHub Actions runs the backend tests and the frontend build + lint on every push and pull request, with no real secrets or external API calls.

---

## Deployment

- **Frontend** — Vercel (static build).
- **Backend + PostgreSQL** — Render.
- **Scheduled sync** — a Render Cron Job running `post_race_weekend_sync.py`.

Full walkthrough, environment variables, and CORS/OAuth notes are in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

---

## Known limitations

- Historical data depends on running the OpenF1 sync per session; only fastest/average lap times are computed, not full per-lap sequences.
- No official race classifications, qualifying results, or grid positions (no source table yet) — finishing order is derived from lap timing.
- No live timing or car telemetry — GridPulse works from stored data, not real-time feeds.
- No Alembic migrations yet; schema changes use `create_tables.py`.

---

## Notes

- `.env` is gitignored — never commit secrets. See [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) for the full variable reference.
- Sync scripts are safe to re-run; they upsert and never create duplicate rows.
- Seeded data currently reflects the configured `F1_SEASON` (default 2026).
