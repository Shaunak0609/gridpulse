# GridPulse

**F1 Race Intelligence Platform**

GridPulse is a Formula 1 companion app for fans who want to follow races more intelligently. It provides driver and team information, race calendars, standings, and will eventually support live race data, user accounts, notifications, and AI-powered race analysis.

This repository contains the backend API built with Python and FastAPI.

---

## Current Status — Phase 9

### Phase 1 — Backend Foundations (complete)

- FastAPI application with clean route structure
- PostgreSQL database connection with SQLAlchemy models
- Pydantic schemas for response validation
- Basic error handling and 404 responses

### Phase 2 — Real F1 Data Ingestion (complete)

- Jolpica F1 API client for fetching external data
- Data ingestion service that maps API responses to database models
- Upsert logic — safe to sync multiple times without creating duplicates
- Manual sync script to pull and store real F1 data for the configured season
- All endpoints now serve real data from the database

### Phase 3 — Frontend Foundation + Multi-Page UI (complete)

- Vite + React + TypeScript frontend in `frontend/`
- Tailwind CSS v4 for styling
- React Router v6 with multi-page navigation
- Pages: Home, Drivers, Driver Detail, Teams, Calendar, Standings
- Loading skeletons, error states, and page entrance animations
- Frontend API service layer pointing at the FastAPI backend

### Phase 4 — User Accounts and Local Authentication (complete)

- `users` table with email, username, password hash, timezone, and created date
- `POST /auth/signup` — create an account with a hashed password
- `POST /auth/login` — verify credentials and receive a JWT access token
- `GET /users/me` — protected endpoint that returns the logged-in user's profile
- JWT tokens signed with a secret key and set to expire after a configurable duration
- Consistent `401` responses for all authentication failures
- Passwords are never stored or returned in plain text

### Phase 4.5 — Frontend Auth UI (complete)

- Login and Signup pages with loading and inline error states
- Auth state management via React Context (AuthContext)
- JWT stored in `localStorage`, restored automatically on page refresh
- Protected `/profile` page — redirects to `/login` if unauthenticated
- Navbar updates based on logged-in state

### Phase 5 — Google Sign-In (complete)

- `users` table extended with `google_sub`, `auth_provider`, and `profile_picture_url`
- `GET /auth/google/start` — redirects browser to Google's account picker
- `GET /auth/google/callback` — exchanges Google auth code for tokens, finds or creates user, returns a GridPulse JWT
- Existing local accounts are automatically linked when the same email is used with Google
- All Google callback errors redirect to `/login` with a human-readable message instead of showing raw JSON
- Frontend "Continue with Google" button on Login and Signup pages
- Frontend `/auth/google/callback` page reads the token from the URL and completes the session
- `GET /users/me` works identically for both local and Google users
- Google Client Secret is never exposed to the frontend

### Phase 6 — Race Calendar and In-App Reminders (complete)

- `reminders` table — stores per-user reminders linked to a race, with a `sent` flag for future delivery
- `notifications` table — stores in-app activity records with a `read` flag and an optional race/driver link
- `POST /reminders` — create a reminder (protected); also creates an in-app notification automatically
- `GET /reminders` — list the current user's reminders, ordered by reminder time (protected)
- `DELETE /reminders/{id}` — delete a reminder; returns 404 if not found, 403 if it belongs to another user (protected)
- `GET /notifications` — list the current user's notifications, newest first (protected)
- `PUT /notifications/{id}/read` — mark a single notification as read (protected)
- `DELETE /notifications/{id}` — delete a notification; returns 404/403 on invalid access (protected)
- Frontend `/reminders` page — lists reminders with delete, loading skeleton, and empty state; requires login
- Frontend `/notifications` page — lists notifications with mark-as-read, delete, unread count badge; requires login
- Calendar page — shows "+ Reminder" button on upcoming races for logged-in users; shows "Log in to remind" for logged-out users
- Navbar — Reminders and Notifications links visible only when logged in
- Duplicate reminder prevention — backend returns `409` if a reminder for the same race already exists; frontend pre-loads existing reminder IDs so the button shows "Reminder set ✓" on page load

### Phase 6.5 — Configurable F1 Season (complete)

- `F1_SEASON` environment variable controls which season is fetched and served (default: `2026`)
- Sync script, calendar endpoint, and standings endpoint all read from `F1_SEASON`
- Calendar and standings filter by season — only the configured season's data is returned

### Phase 7 — Email Notifications (complete)

- Three opt-in email preference fields added to the `users` table: `email_notifications_enabled`, `calendar_email_reminders_enabled`, `favorite_driver_email_alerts_enabled` (all default `false`)
- `email_sent` and `email_sent_at` tracking columns added to the `reminders` table
- `GET /users/me/email-preferences` — returns the current user's email preference settings (protected)
- `PUT /users/me/email-preferences` — updates one or more email preferences (partial update; protected)
- `POST /email/test` — sends a test email to the current user; requires `email_notifications_enabled = true` (protected)
- `POST /email/send-due-reminders` — development endpoint to manually trigger delivery of all due reminder emails (protected)
- Email delivery via **Resend** — `app/services/email_service.py` wraps the Resend SDK; all Resend errors are normalised to `RuntimeError` so callers have a single exception type to handle
- `app/services/reminder_email_service.py` — shared delivery logic: queries due, unsent reminders for opted-in users, sends each email, marks `email_sent = true`, and returns a `{total, sent, failed}` summary
- `scripts/send_due_reminder_emails.py` — standalone CLI script that calls the same service; intended for use with a cron job or scheduler in production
- Frontend `/settings` page — email preference toggles with optimistic UI updates; "Send test email" button visible when the master switch is on; requires login
- Navbar — Settings link visible only when logged in

### Phase 7.5 — Session Schedule Support (complete)

- `sessions` table — stores individual sessions per race (Practice 1–3, Qualifying, Sprint, Race) with `session_type`, `session_name`, `start_time`, `end_time`, and `timezone`
- Unique constraint on `(race_id, session_type)` — sync is safe to run multiple times without creating duplicate sessions
- `session_id` nullable foreign key added to the `reminders` table — allows a reminder to target a specific session rather than just a race weekend
- `GET /races/{race_id}/sessions` — returns all sessions for a race, ordered by start time (public)
- `GET /sessions/upcoming` — returns the next N upcoming sessions for the current season, ordered by start time (public, default limit 10)
- `ReminderCreate` and `ReminderResponse` updated to accept and return optional `session_id`
- When `session_id` is provided, the backend validates the session exists and auto-populates `race_id` from the session — no mismatch possible
- Duplicate check is session-aware: one reminder per `(user_id, session_id)` for session reminders, one per `(user_id, race_id)` for race reminders
- Due-reminder email service (`reminder_email_service.py`) updated — session reminders produce a more specific subject and body: `"Qualifying – Australian Grand Prix"` instead of just the race name
- Frontend Calendar page — each race row has a chevron to expand a session panel; sessions load on demand (lazy fetch); each upcoming session shows a `+ Remind` button
- Session reminder buttons are colour-coded by type: slate for practice, amber for qualifying, orange for sprint sessions, red for race
- Pre-load check on Calendar page load — session reminder buttons show "Reminder set ✓" immediately if a reminder already exists
- Frontend Reminders page — session reminders show a session-type badge (e.g. "Qualifying") and a colour-coded dot; race reminders show a "Race" badge
- `scripts/seed_sessions.py` — seeds five standard sessions per race derived from each race's `start_date`; safe to run multiple times

### Phase 9 — Favourite Driver Notifications, Non-Live (complete)

- `favorite_driver_notifications_enabled` boolean column added to the `users` table — controls in-app notification delivery per user (defaults to `true`; opt-out model)
- `GET /users/me/notification-preferences` — returns the current user's in-app notification preferences (protected)
- `PUT /users/me/notification-preferences` — updates one or more notification preferences; partial update, any field can be omitted (protected)
- `NotificationPreferences` and `NotificationPreferencesUpdate` Pydantic schemas added to `app/schemas/user.py`
- `scripts/migrate_add_favorite_driver_notifications.py` — idempotent migration to add `favorite_driver_notifications_enabled` to an existing `users` table
- `app/services/favorite_driver_notifications.py` — batch notification generation service with two functions:
  - `generate_standing_notifications` — creates one `favorite_driver_standing` in-app notification per (user, driver) summarising the driver's championship position and points
  - `generate_wins_notifications` — creates one `favorite_driver_wins` in-app notification per (user, driver) when the driver has at least one win in the configured season, derived from the existing `DriverStanding.wins` column
- Both functions apply three rules in order: skip opted-out users → skip drivers with no standing data → skip (user, driver) pairs that already have a notification of that type (dedup)
- `scripts/generate_favorite_driver_notifications.py` — CLI script that runs both generators and prints a result block per type showing checked, created, skipped, and email counts; includes a tip to delete existing rows for regeneration
- Optional email delivery — after each new notification is committed, an email is sent if the user has `email_notifications_enabled` and `favorite_driver_email_alerts_enabled` both set to `true`; the notification row is always saved first so in-app delivery is never lost if the email fails
- Frontend `NotificationPreferences` type and `getNotificationPreferences` / `updateNotificationPreferences` API functions added
- Frontend Settings page (`/settings`) — loads email and notification preferences in parallel via `Promise.all`; new **Driver Notifications** section with two toggles: "In-app notifications" (`favorite_driver_notifications_enabled`) and "Email alerts" (`favorite_driver_email_alerts_enabled`); email alerts toggle is disabled when the master email switch is off; optimistic UI updates with revert on failure
- Frontend Notifications page (`/notifications`) — `favorite_driver_standing` and `favorite_driver_wins` notifications are visually distinguished from other types: amber filled-star icon in the left gutter (replaces the red/gray unread dot), and a type-specific badge inline with the title ("Driver update" for standings, "Race wins" for wins); all read/mark-read/delete behaviour unchanged
- Frontend Dashboard page (`/dashboard`) — "Driver Updates" section placed below Favourite Drivers shows the three most recent `favorite_driver_standing` or `favorite_driver_wins` notifications with the amber star treatment; non-driver notifications render in a separate "Recent Notifications" section that only appears when non-driver notifications exist; both sections link to `/notifications`

**What notifications are currently supported:**

| Type | Title | Trigger | Message example |
|---|---|---|---|
| `favorite_driver_standing` | Favourite driver update | Manual script run | "Max Verstappen is currently P1 in the 2026 driver standings with 136 points." |
| `favorite_driver_wins` | Race wins update | Manual script run, only when wins > 0 | "Max Verstappen has 3 wins in the 2026 season." |

**What is not yet supported:**
- Per-race finish position notifications — requires a `race_results` table (no race result data ingested yet)
- Per-qualifying position notifications — requires a `qualifying_results` table
- Automatic or scheduled notification generation — currently manual only via `scripts/generate_favorite_driver_notifications.py`
- Live or real-time alerts of any kind

### Phase 8 — Favourite Drivers, Favourite Teams, and Personalised Dashboard (complete)

- `favorite_drivers` table — stores one row per `(user_id, driver_id)` pair; unique constraint `uq_favorite_driver_user` prevents duplicate favourites
- `favorite_teams` table — same pattern with `(user_id, team_id)` and unique constraint `uq_favorite_team_user`
- `FavoriteDriver` and `FavoriteTeam` SQLAlchemy models with relationships to `User`, `Driver`, and `Team`
- Nested Pydantic schemas: `FavoriteDriverResponse` embeds a full `FavoriteDriverInfo` (including the driver's team as `FavoriteTeamInfo`); `FavoriteTeamResponse` embeds `FavoriteTeamInfo`
- `GET /me/favorites/drivers` — returns the current user's favourite drivers, ordered by when they were added (protected)
- `POST /me/favorites/drivers/{driver_id}` — favourites a driver; returns `404` if the driver does not exist, `409` if already favourited (protected)
- `DELETE /me/favorites/drivers/{driver_id}` — removes a favourite driver; returns `404` if not in the user's list (protected)
- `GET /me/favorites/teams` — returns the current user's favourite teams, ordered by when they were added (protected)
- `POST /me/favorites/teams/{team_id}` — favourites a team; returns `404` if the team does not exist, `409` if already favourited (protected)
- `DELETE /me/favorites/teams/{team_id}` — removes a favourite team; returns `404` if not in the user's list (protected)
- `GET /me/dashboard` — returns a personalised summary in one request: user profile, favourite drivers (with nested team info), favourite teams, next 5 upcoming sessions, next 5 upcoming reminders, 5 most recent notifications (protected)
- Frontend favourite API functions: `getFavoriteDrivers`, `addFavoriteDriver`, `removeFavoriteDriver`, `getFavoriteTeams`, `addFavoriteTeam`, `removeFavoriteTeam`, `getDashboard`
- Driver Detail page — star button appears for logged-in users; initial state loaded from `GET /me/favorites/drivers` on mount; toggles between ☆ Add to Favourites and ★ Favourited; logged-out users see a styled "Log in to favourite" prompt that matches the button shape
- Teams page — each team card has an individual star button; initial state is pre-loaded from `GET /me/favorites/teams` on page load; card border turns red when favourited; logged-out users see a "Log in to favourite" prompt per card
- Dashboard page (`/dashboard`) — protected route; shows six sections: Welcome heading, Favourite Drivers (with driver number and team, links to driver detail pages), Favourite Teams, Upcoming Sessions (colour-coded by session type), Upcoming Reminders, and Recent Notifications (unread highlighted in red)
- Dashboard link added to the navbar — visible only when logged in
- All Dashboard sections show informative empty states with dashed-border cards and action links pointing to the relevant page (Drivers, Teams, Calendar) — not blank areas
- All session and reminder times display in the user's local browser timezone, not hard-coded UTC
- `scripts/migrate_create_favorites_tables.py` — idempotent migration to add `favorite_drivers` and `favorite_teams` to an existing database; fresh databases use `create_tables.py` directly

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
| Password hashing | passlib + bcrypt |
| JWT tokens | python-jose |
| Google OAuth | google-auth |
| Email delivery | Resend |
| Frontend | React + Vite + TypeScript |
| Styling | Tailwind CSS v4 |
| Routing | React Router v6 |

---

## External Data Source

**Jolpica F1 API** — `https://api.jolpi.ca/ergast/f1`

Jolpica is a free, public Formula 1 data API. No API key is required. GridPulse uses it to fetch:

| Data | Jolpica endpoint |
|---|---|
| Race calendar | `/{season}/races.json` |
| Driver standings | `/{season}/driverStandings.json` |
| Constructor standings | `/{season}/constructorStandings.json` |

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
│   ├── auth/
│   │   ├── dependencies.py       # get_current_user dependency for protected routes
│   │   ├── google_oauth.py       # Google ID token verification utility
│   │   └── security.py           # password hashing and JWT utilities
│   ├── database/
│   │   └── database.py           # DB engine, session, Base
│   ├── models/
│   │   ├── team.py
│   │   ├── driver.py
│   │   ├── race.py
│   │   ├── standing.py
│   │   ├── user.py               # User model (Phase 4)
│   │   ├── reminder.py           # Reminder model — race_id + session_id (Phase 6/7.5)
│   │   ├── notification.py       # Notification model (Phase 6)
│   │   ├── session.py            # Session model (Phase 7.5)
│   │   ├── favorite_driver.py    # FavoriteDriver model — user/driver join table (Phase 8)
│   │   └── favorite_team.py      # FavoriteTeam model — user/team join table (Phase 8)
│   ├── schemas/
│   │   ├── team.py
│   │   ├── driver.py
│   │   ├── race.py
│   │   ├── standing.py
│   │   ├── user.py               # UserCreate, UserLogin, UserResponse, Token
│   │   ├── reminder.py           # ReminderCreate/Response with optional session_id (Phase 6/7.5)
│   │   ├── notification.py       # NotificationResponse (Phase 6)
│   │   ├── session.py            # SessionCreate, SessionResponse (Phase 7.5)
│   │   ├── favorite.py           # FavoriteDriverResponse, FavoriteTeamResponse + nested info schemas (Phase 8)
│   │   └── dashboard.py          # DashboardResponse — assembles all sections (Phase 8)
│   ├── routes/
│   │   ├── auth.py               # POST /auth/signup, POST /auth/login
│   │   ├── google_auth.py        # GET /auth/google/start, GET /auth/google/callback
│   │   ├── users.py              # GET /users/me, email-preferences, notification-preferences (Phase 7/9)
│   │   ├── drivers.py
│   │   ├── teams.py
│   │   ├── calendar.py
│   │   ├── standings.py
│   │   ├── reminders.py          # POST/GET/DELETE /reminders (Phase 6/7.5)
│   │   ├── notifications.py      # GET/PUT/DELETE /notifications (Phase 6)
│   │   ├── email.py              # POST /email/test, POST /email/send-due-reminders (Phase 7)
│   │   ├── sessions.py           # GET /sessions/upcoming, GET /races/{id}/sessions (Phase 7.5)
│   │   ├── favorites.py          # GET/POST/DELETE /me/favorites/drivers + /teams (Phase 8)
│   │   └── dashboard.py          # GET /me/dashboard (Phase 8)
│   ├── services/
│   │   ├── f1_api_client.py      # HTTP client for Jolpica API
│   │   ├── data_ingestion.py     # maps API data into SQLAlchemy models
│   │   ├── email_service.py      # Resend wrapper (Phase 7)
│   │   ├── reminder_email_service.py  # due-reminder delivery; session-aware email body (Phase 7/7.5)
│   │   └── favorite_driver_notifications.py  # standing + wins notification generators (Phase 9)
│   └── main.py
├── frontend/                     # React + Vite + TypeScript frontend (Phase 3)
├── scripts/
│   ├── create_tables.py          # creates all tables including sessions
│   ├── seed.py                   # inserts small local sample data (Phase 1)
│   ├── sync_f1_data.py           # fetches and stores real F1 data from Jolpica
│   ├── seed_sessions.py          # seeds 5 standard sessions per race (Phase 7.5)
│   ├── migrate_add_email_preferences.py        # adds email preference columns to users (Phase 7)
│   ├── migrate_add_reminder_email_tracking.py  # adds email_sent columns to reminders (Phase 7)
│   ├── migrate_create_sessions_table.py        # creates sessions table (Phase 7.5)
│   ├── migrate_add_reminder_session_id.py      # adds session_id to reminders (Phase 7.5)
│   ├── migrate_create_favorites_tables.py           # creates favorite_drivers and favorite_teams tables (Phase 8)
│   ├── migrate_add_favorite_driver_notifications.py # adds favorite_driver_notifications_enabled to users (Phase 9)
│   ├── send_due_reminder_emails.py                  # CLI script to send due reminder emails (Phase 7)
│   └── generate_favorite_driver_notifications.py    # CLI script to generate standing + wins notifications (Phase 9)
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

Open `.env` and fill in your database credentials, JWT settings, Google OAuth credentials, and email settings:

```
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/gridpulse_db

JWT_SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-client-secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/auth/google/callback
FRONTEND_URL=http://localhost:5173

F1_SEASON=2026

RESEND_API_KEY=re_your_api_key_here
EMAIL_FROM=GridPulse <you@yourdomain.com>
```

`RESEND_API_KEY` — create a free account at [resend.com](https://resend.com), go to **API Keys**, and generate a key.

`EMAIL_FROM` — the sender address shown in outgoing emails. With a free Resend account the only verified sender is `onboarding@resend.dev`, which can only deliver to the email address you registered with. To send to other addresses, verify your own domain in the Resend dashboard.

Replace `your_username` and `your_password` with your actual PostgreSQL credentials. Your username is usually your Mac username — run `whoami` in the terminal if you are unsure.

To generate a secure `JWT_SECRET_KEY`, run:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output into your `.env` file. Never commit this value to git.

`GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` come from Google Cloud Console — see the Google OAuth Setup section below.

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
  - users
  - reminders
  - notifications
```

### 7. Sync real F1 data from Jolpica

```bash
python scripts/sync_f1_data.py
```

This fetches F1 data for the season set in `F1_SEASON` (default: 2026) from the Jolpica API and stores it in your database. An internet connection is required.

Expected output:

```
=== GridPulse F1 Data Sync — 2026 season ===

[Teams]
  Fetching: https://api.jolpi.ca/ergast/f1/2026/constructorStandings.json
  OK — 10 inserted, 0 updated.

[Drivers]
  Fetching: https://api.jolpi.ca/ergast/f1/2026/driverStandings.json
  OK — 20 inserted, 0 updated, 0 skipped.

[Race Calendar]
  Fetching: https://api.jolpi.ca/ergast/f1/2026/races.json?limit=100
  OK — 24 inserted, 0 updated.

[Driver Standings]
  Fetching: https://api.jolpi.ca/ergast/f1/2026/driverStandings.json
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

## Changing the F1 Season

The season GridPulse syncs is controlled by the `F1_SEASON` variable in your `.env` file. The default is `2026`.

To switch to a different season:

1. Open your `.env` file and change the value:
   ```
   F1_SEASON=2025
   ```
2. Run the sync script:
   ```bash
   python scripts/sync_f1_data.py
   ```
   The script will fetch data for the new season and upsert it into the database. Existing rows for other seasons are not deleted — the database can hold multiple seasons at once.

3. Restart the backend so the updated season is in effect:
   ```bash
   uvicorn app.main:app --reload
   ```

**Notes:**
- Jolpica only has complete data for seasons that have started. Requesting a future season that has no data yet will return empty results and the sync will warn you.
- The standings endpoint (`GET /standings/drivers`) queries the database for whichever season's data was most recently synced. If you sync a new season, standings will update automatically on the next request.
- The calendar endpoint (`GET /calendar`) returns all races in the database across all seasons. To limit to one season, that filtering can be added in a future phase.

---

## Google OAuth Setup

Google sign-in requires a one-time manual setup in Google Cloud Console.

1. Go to [console.cloud.google.com](https://console.cloud.google.com) and create a new project named `GridPulse`.
2. Navigate to **APIs & Services → OAuth consent screen**. Choose **External**, fill in the app name and your email, then add yourself as a test user.
3. Navigate to **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**.
   - Application type: **Web application**
   - Name: `GridPulse Dev`
   - Authorised JavaScript origins: `http://localhost:5173`
   - Authorised redirect URIs: `http://127.0.0.1:8000/auth/google/callback`
4. Copy the **Client ID** and **Client Secret** into your `.env` file.

**Important:** `GOOGLE_REDIRECT_URI` must use `127.0.0.1`, not `localhost`, and must match the URI registered in Google Cloud Console exactly.

### Testing Google Sign-In

1. Start the backend: `uvicorn app.main:app --reload`
2. Start the frontend: `cd frontend && npm run dev`
3. Open `http://localhost:5173/login` and click **Continue with Google**.
4. Select your test Google account in the popup.
5. You should be redirected back to the frontend, logged in, with your Google email in the navbar.
6. Visit `/profile` — `auth_provider` shows `local` if you previously had an email/password account with the same address (accounts are linked), or `google` if this was a fresh sign-up.
7. `GET /users/me` works the same way for Google users as it does for local users — the backend only checks the GridPulse JWT, not the original auth method.

**Common problems:**

| Problem | Fix |
|---|---|
| `redirect_uri_mismatch` | The URI in `.env` doesn't exactly match what you registered. Check `127.0.0.1` vs `localhost`. |
| "Access blocked: app not verified" | Add your Gmail to the test users list in OAuth consent screen. |
| Redirected to `/login` with an error message | Check that `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` are correctly set in `.env`. |

---

## Available Endpoints

### Public endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Welcome message |
| GET | `/health` | Health check |
| GET | `/drivers` | List all 20 drivers |
| GET | `/drivers/{id}` | Get a single driver by ID |
| GET | `/teams` | List all 10 teams |
| GET | `/calendar` | Race calendar for the configured season |
| GET | `/standings/drivers` | Driver championship standings |
| GET | `/races/{race_id}/sessions` | All sessions for a specific race, ordered by start time |
| GET | `/sessions/upcoming` | Next N upcoming sessions for the current season (default 10, max 50) |

### Authentication endpoints

| Method | Endpoint | Auth required | Description |
|---|---|---|---|
| POST | `/auth/signup` | No | Create a new user account |
| POST | `/auth/login` | No | Log in and receive a JWT token |
| GET | `/auth/google/start` | No | Redirect browser to Google sign-in |
| GET | `/auth/google/callback` | No | Handle Google redirect, return JWT |
| GET | `/users/me` | Yes — Bearer token | Return the logged-in user's profile |
| GET | `/users/me/email-preferences` | Yes — Bearer token | Return the current user's email preferences |
| PUT | `/users/me/email-preferences` | Yes — Bearer token | Update one or more email preferences |
| GET | `/users/me/notification-preferences` | Yes — Bearer token | Return the current user's in-app notification preferences |
| PUT | `/users/me/notification-preferences` | Yes — Bearer token | Update one or more in-app notification preferences |

### Reminder endpoints

All reminder endpoints require a valid JWT Bearer token. Requests without a token return `401`. Requests for another user's reminder return `403`.

| Method | Endpoint | Auth required | Description |
|---|---|---|---|
| POST | `/reminders` | Yes — Bearer token | Create a reminder; accepts optional `session_id` for session-level reminders |
| GET | `/reminders` | Yes — Bearer token | List the current user's reminders; includes `session_id` in response |
| DELETE | `/reminders/{id}` | Yes — Bearer token | Delete a reminder by ID |

### Notification endpoints

All notification endpoints require a valid JWT Bearer token.

| Method | Endpoint | Auth required | Description |
|---|---|---|---|
| GET | `/notifications` | Yes — Bearer token | List the current user's notifications, newest first |
| PUT | `/notifications/{id}/read` | Yes — Bearer token | Mark a notification as read |
| DELETE | `/notifications/{id}` | Yes — Bearer token | Delete a notification by ID |

### Favourite endpoints

All favourite endpoints require a valid JWT Bearer token. Users can only read and modify their own favourites.

| Method | Endpoint | Auth required | Description |
|---|---|---|---|
| GET | `/me/favorites/drivers` | Yes — Bearer token | List the current user's favourite drivers, with nested driver and team info |
| POST | `/me/favorites/drivers/{driver_id}` | Yes — Bearer token | Favourite a driver; `404` if driver not found; `409` if already favourited |
| DELETE | `/me/favorites/drivers/{driver_id}` | Yes — Bearer token | Remove a favourite driver; `404` if not in the user's list |
| GET | `/me/favorites/teams` | Yes — Bearer token | List the current user's favourite teams, with nested team info |
| POST | `/me/favorites/teams/{team_id}` | Yes — Bearer token | Favourite a team; `404` if team not found; `409` if already favourited |
| DELETE | `/me/favorites/teams/{team_id}` | Yes — Bearer token | Remove a favourite team; `404` if not in the user's list |
| GET | `/me/dashboard` | Yes — Bearer token | Personalised summary: user profile, favourite drivers and teams, next 5 sessions, next 5 reminders, 5 most recent notifications |

### Email endpoints

| Method | Endpoint | Auth required | Description |
|---|---|---|---|
| POST | `/email/test` | Yes — Bearer token | Send a test email to the current user; requires `email_notifications_enabled = true` |
| POST | `/email/send-due-reminders` | Yes — Bearer token | Development endpoint — send all due, unsent reminder emails now |

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
    "season": 2026,
    "round": 1,
    "name": "Australian Grand Prix",
    "circuit_name": "Albert Park Grand Prix Circuit",
    "country": "Australia",
    "start_date": "2026-03-15"
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

## Testing Authentication

All auth endpoints can be tested at `http://127.0.0.1:8000/docs` while the server is running.

### Test signup

1. Open `/docs` and find **POST /auth/signup**.
2. Click **Try it out** and enter:
    ```json
    {
      "email": "test@example.com",
      "password": "password123"
    }
    ```
3. Click **Execute**. You should get a `201` response with your user profile — no `password_hash` field will appear.
4. Send the same request again. You should get a `400` — "An account with that email already exists."

### Test login

1. Find **POST /auth/login**.
2. Click **Try it out** and enter:
    ```json
    {
      "email": "test@example.com",
      "password": "password123"
    }
    ```
3. Click **Execute**. You should get a `200` response with an `access_token` string and `"token_type": "bearer"`.
4. Copy the `access_token` value (the long string, without the quotes).
5. Try logging in with a wrong password. You should get a `401` — "Incorrect email or password."

### Test GET /users/me

1. Click the **Authorize** padlock button at the top right of the `/docs` page.
2. In the **HTTPBearer** field, paste the token you copied from the login response. Click **Authorize**, then **Close**.
3. Find **GET /users/me** → **Try it out** → **Execute**. You should get a `200` with your user profile.
4. To test the failure case: click **Authorize** again → **Logout**, then try **GET /users/me** again. You should get a `401` — "Not authenticated."

---

## Interactive API Docs

FastAPI generates interactive documentation automatically.

Open `http://127.0.0.1:8000/docs` in your browser while the server is running. You can browse every endpoint, see the expected response shape, and test requests directly from the browser without any extra tools.

---

## Testing Reminders and Notifications

### Test reminders in FastAPI docs

1. Start the backend: `uvicorn app.main:app --reload`
2. Open `http://127.0.0.1:8000/docs`
3. Log in via **POST /auth/login** and copy the `access_token`
4. Click the **Authorize** padlock, paste the token, click **Authorize**
5. Find **POST /reminders** → **Try it out** and enter:
   ```json
   {
     "title": "Monaco Grand Prix – Race Day",
     "reminder_time": "2026-05-25T09:00:00Z",
     "race_id": 6
   }
   ```
6. Click **Execute** — you should get a `201` response with the new reminder
7. Call **GET /reminders** — your reminder should appear
8. Call **GET /notifications** — you should see a `"reminder_created"` notification created automatically
9. Call **PUT /notifications/{id}/read** with the notification's ID — `read` should become `true`
10. Call **DELETE /reminders/{id}** with the reminder's ID — you should get `204 No Content`

### Test reminders in the frontend

1. Start both servers: `uvicorn app.main:app --reload` and `cd frontend && npm run dev`
2. Log in at `http://localhost:5173/login`
3. Go to `/calendar` — upcoming race rows should show a "+ Reminder" button (visible once the 2026 race data is seeded)
4. Click "+ Reminder" — button should briefly show "Adding…" then switch to "Reminder set ✓"
5. Go to `/reminders` — the new reminder should appear in the list
6. Click the trash icon to delete it — the row should disappear immediately

### Test notifications in the frontend

1. After creating a reminder (see above), go to `/notifications`
2. You should see a "Reminder created" notification with a red unread dot and an unread count badge in the header
3. Click **Mark read** — the row dims, the dot turns grey, and the button disappears
4. Click the trash icon — the row disappears and the count badge updates
5. Log out and try navigating to `/notifications` directly — you should be redirected to `/login`

---

## Testing Email Notifications

### Set up email credentials

Make sure `RESEND_API_KEY` and `EMAIL_FROM` are set in your `.env` file before testing. Restart the backend after editing `.env`.

### Enable email preferences via the frontend

1. Start both servers: `uvicorn app.main:app --reload` and `cd frontend && npm run dev`
2. Log in and go to `http://localhost:5173/settings`
3. Toggle **Email notifications** on (master switch)
4. Toggle **Race reminder emails** on
5. Click **Send test email** — you should receive an email at your registered address within a few seconds

### Enable email preferences via the API docs

1. Open `http://127.0.0.1:8000/docs`, log in, and authorize
2. Find **PUT /users/me/email-preferences** → **Try it out** and enter:
   ```json
   {
     "email_notifications_enabled": true,
     "calendar_email_reminders_enabled": true
   }
   ```
3. Click **Execute** — you should get a `200` response with both fields set to `true`
4. Find **POST /email/test** → **Try it out** → **Execute** — you should receive a test email

### Test due reminder delivery

1. Create a reminder for a race whose `start_date` is in the past, or manually insert a reminder row with `reminder_time` in the past via psql
2. Call **POST /email/send-due-reminders** in the API docs — the response will show `total_due`, `sent`, and `failed` counts
3. Alternatively, run the CLI script directly:
   ```bash
   python scripts/send_due_reminder_emails.py
   ```
   Expected output:
   ```
   Found 1 due reminder(s).
   Sent: 1  Failed: 0
   ```
4. Running either the endpoint or the script again immediately will show `total_due: 0` because processed reminders are marked `email_sent = true`

---

## Session Schedule Setup and Testing

### Create the sessions table

If you have an existing database (already has races, users, reminders), run the migration:

```bash
python scripts/migrate_create_sessions_table.py
python scripts/migrate_add_reminder_session_id.py
```

Both scripts use `IF NOT EXISTS` / `ADD COLUMN IF NOT EXISTS` and are safe to run more than once.

If you are setting up a fresh database, `create_tables.py` creates the `sessions` table automatically — no migration scripts needed.

### Seed session data

After the table exists and races are synced, seed five standard sessions per race:

```bash
python scripts/seed_sessions.py
```

Expected output (24 races × 5 sessions):
```
Found 24 race(s). Seeding sessions...
Done. 120 session(s) inserted, 0 already existed.
```

Running it again produces:
```
Done. 0 session(s) inserted, 120 already existed.
```

Session times are derived from each race's `start_date`:
- Practice 1 — Friday 10:30 UTC
- Practice 2 — Friday 14:00 UTC
- Practice 3 — Saturday 11:30 UTC
- Qualifying — Saturday 15:00 UTC
- Race — Sunday 13:00 UTC

These are approximations. Once real session times are synced from Jolpica or another source, the seed values can be replaced with a re-run of the sync.

### Test session endpoints in API docs

1. Start the backend: `uvicorn app.main:app --reload`
2. Open `http://127.0.0.1:8000/docs`
3. Call `GET /races/1/sessions` — you should see 5 sessions for round 1, ordered by start time
4. Call `GET /sessions/upcoming` — next 10 sessions with a future `start_time` are returned
5. Call `GET /sessions/upcoming?limit=3` — returns exactly 3 sessions
6. Call `GET /races/9999/sessions` — you should get a `404` response

### Test session reminders in the frontend

1. Start both servers: `uvicorn app.main:app --reload` and `cd frontend && npm run dev`
2. Log in and go to `/calendar`
3. Click the chevron `›` on any upcoming race row — five sessions appear beneath it
4. Click `+ Remind` on Practice 1 — button shows "Adding…" then "Reminder set ✓"
5. Click `+ Remind` on Qualifying (same race) — sets independently
6. Click `+ Remind` on Practice 1 again — backend returns `409`; button shows the error
7. Go to `/reminders` — both session reminders appear with session-type badges and colour-coded dots
8. Reload `/calendar` and expand the same race — both session buttons already show "Reminder set ✓"

---

## Testing Favourites and the Dashboard

### Set up the database tables

If you have an existing database (already has users, reminders, sessions), run the migration:

```bash
python scripts/migrate_create_favorites_tables.py
```

Expected output:
```
Running migration: create favorite_drivers and favorite_teams tables...
Done. favorite_drivers and favorite_teams tables created (or already existed — safe to run again).
```

If you are setting up a fresh database, `create_tables.py` creates both tables automatically — no migration needed.

### Test favourites in FastAPI docs

1. Start the backend: `uvicorn app.main:app --reload`
2. Open `http://127.0.0.1:8000/docs`
3. Log in via **POST /auth/login** and copy the `access_token`
4. Click the **Authorize** padlock at the top right, paste the token, click **Authorize**

**Favourite a driver:**

5. Find **POST /me/favorites/drivers/{driver_id}** → **Try it out**
6. Enter a valid `driver_id` (e.g. `1`) and click **Execute** — you should get a `201` response with the favourite record including nested driver and team info
7. Try the same request again — you should get `409 Conflict`: "You have already favourited this driver."
8. Find **GET /me/favorites/drivers** → **Execute** — your favourited driver should appear in the list
9. Find **DELETE /me/favorites/drivers/{driver_id}** → enter `1` → **Execute** — you should get `204 No Content`
10. Call **GET /me/favorites/drivers** again — the list should now be empty

**Favourite a team:**

11. Follow the same steps using `/me/favorites/teams/{team_id}` with a valid `team_id` (e.g. `1`)

**Test the dashboard:**

12. Add one or two favourite drivers and teams (steps above)
13. Find **GET /me/dashboard** → **Execute** — the response includes `user`, `favorite_drivers`, `favorite_teams`, `upcoming_sessions`, `upcoming_reminders`, and `recent_notifications`
14. `upcoming_sessions` shows the next 5 sessions from the current season; `upcoming_reminders` shows your next 5 reminders; `recent_notifications` shows the 5 most recent

**Test invalid cases:**

15. Call **POST /me/favorites/drivers/9999** — you should get `404`: "Driver with id 9999 not found."
16. Call **DELETE /me/favorites/drivers/1** when it is not in your list — you should get `404`: "Favourite not found."

### Test favourites in the frontend

**Driver Detail — favourite a driver:**

1. Start both servers: `uvicorn app.main:app --reload` and `cd frontend && npm run dev`
2. Log in and go to `/drivers`
3. Click any driver to open their detail page
4. You should see a `☆ Add to Favourites` button in the top right of the header
5. Click it — the button briefly shows "Adding…" then switches to `★ Favourited`
6. Click it again — it shows "Removing…" then returns to `☆ Add to Favourites`
7. Log out and revisit the same driver page — the button area now shows `☆ Log in to favourite` and the sub-text "Sign in to follow this driver"

**Teams page — favourite a team:**

8. Log in and go to `/teams`
9. Each team card shows `☆ Log in to favourite` if you are logged out, or `☆ Add to Favourites` if logged in
10. Click the star on any team card — it briefly shows "Adding…" then `★ Favourited`; the card border turns red
11. Click again to unfavourite — border returns to grey
12. Log out and reload `/teams` — every card shows `☆ Log in to favourite` and "Sign in to follow this team"

**Dashboard:**

13. Log in and click **Dashboard** in the navbar
14. If you have no favourites yet, you should see dashed-border empty state cards with explanatory text and a "Browse …" action button for each favourites section
15. Favourite one or two drivers and one team, then return to `/dashboard` — the relevant sections fill in with cards
16. Click a driver card in the Favourite Drivers section — it should link directly to that driver's detail page
17. Click the "Browse teams →" button in the empty Teams section — it should navigate to `/teams`
18. Log out and try to navigate to `/dashboard` directly — you should be redirected to `/login`

---

## Testing Favourite Driver Notifications

### Set up the database column

If you have an existing database, run the migration to add the new user preference column:

```bash
python scripts/migrate_add_favorite_driver_notifications.py
```

Fresh databases created with `create_tables.py` already include the column — no migration needed.

### Generate notifications manually

Make sure the virtual environment is active and the backend is not required to be running for this step:

```bash
source venv/bin/activate
python scripts/generate_favorite_driver_notifications.py
```

Expected output (first run, after favouriting at least one driver):

```
Favourite-driver notifications — generation complete.

Standing notifications:
  Favourite drivers checked : 1
  Notifications created     : 1
  Skipped (duplicate)       : 0
  Skipped (no standing data): 0
  Skipped (opted out)       : 0
  Emails sent               : 1
  Emails failed             : 0

Wins notifications:
  Favourite drivers checked : 1
  Notifications created     : 1
  Skipped (duplicate)       : 0
  Skipped (no standing data): 0
  Skipped (no wins yet)     : 0
  Skipped (opted out)       : 0
  Emails sent               : 1
  Emails failed             : 0
```

Running the script again immediately will show `Notifications created: 0` and a tip about deleting existing rows. To regenerate:

```sql
DELETE FROM notifications WHERE type IN ('favorite_driver_standing', 'favorite_driver_wins');
```

### Test notification preferences in the frontend

1. Start both servers: `uvicorn app.main:app --reload` and `cd frontend && npm run dev`
2. Log in and go to `http://localhost:5173/settings`
3. The page loads **Email Notifications** and **Driver Notifications** sections simultaneously
4. In **Driver Notifications**: toggle "In-app notifications" off — the backend should save immediately (optimistic update)
5. Run the script — affected users should be counted under "Skipped (opted out)"
6. Toggle it back on and re-run — notifications should be created again (after deleting existing rows)
7. The **Email alerts** toggle under Driver Notifications is disabled when the master email switch is off

### Test the Notifications page

1. Go to `http://localhost:5173/notifications`
2. `favorite_driver_standing` notifications should show an amber star icon and a **"Driver update"** badge
3. `favorite_driver_wins` notifications should show the same amber star and a **"Race wins"** badge
4. Mark one as read — the star turns grey and the row dims to 50% opacity
5. Delete one — the row is removed immediately

### Test the Dashboard Driver Updates section

1. Go to `http://localhost:5173/dashboard`
2. The **Driver Updates** section appears below Favourite Drivers and shows up to 3 recent `favorite_driver_standing` or `favorite_driver_wins` notifications with amber stars
3. Unread notifications show a small amber dot in the top-right of the card; read ones are dimmed
4. The "All notifications →" link goes to `/notifications`
5. If you have no driver update notifications yet, the section shows an empty state with a "Browse drivers" link

---

## What Is Not Included Yet

The following features are planned but not yet built:

- Per-race finish position notifications — requires a `race_results` table; no race result data is ingested yet
- Per-qualifying position notifications — requires a `qualifying_results` table
- Automatic or scheduled notification generation — currently manual only via `scripts/generate_favorite_driver_notifications.py`
- Session times are seeded from approximate UTC values, not pulled live from Jolpica — real session times from the API will be added in a future sync update
- Push notifications
- Scheduled or automatic reminder delivery — the delivery logic exists but no background job or cron runs it yet; use `scripts/send_due_reminder_emails.py` or `POST /email/send-due-reminders` manually for now
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
- Alembic database migrations

---

## Future Phases

**Phase 3 — Frontend Foundation + Multi-Page UI** *(complete)*
React frontend with Tailwind CSS and React Router. Pages: Home, Drivers, Driver Detail, Teams, Calendar, Standings.

**Phase 4 — User Accounts and Local Authentication** *(complete)*
Email and password authentication with JWT tokens. Users can sign up, log in, and access protected routes.

**Phase 5 — Google Sign-In** *(complete)*
Google OAuth via Authorization Code flow. Users can sign in with their Google account. Existing local accounts are linked automatically by email.

**Phase 6 — Race Calendar and In-App Reminders** *(complete)*
Signed-in users can set reminders for upcoming races from the Calendar page. Reminders and in-app notifications are stored in the database and viewable in the frontend.

**Phase 7 — Email Notifications** *(complete)*
Opt-in email preferences, Resend integration, test email endpoint, due-reminder delivery service, CLI script, and a frontend Settings page for managing preferences.

**Phase 7.5 — Session Schedule Support** *(complete)*
Sessions table and model for FP1–FP3, Sprint, Qualifying, and Race. Session-aware reminders, session endpoints, Calendar page session panels with per-session reminder buttons, and session-specific email bodies.

**Phase 8 — Favourite Drivers, Favourite Teams, and Personalised Dashboard** *(complete)*
Users can favourite drivers and teams. A protected Dashboard page shows a personalised summary: favourite drivers and teams, upcoming sessions, reminders, and recent notifications. All times display in the user's local timezone.

**Phase 9 — Favourite Driver Notifications, Non-Live** *(complete)*
In-app and optional email notifications for favourited drivers. Two notification types are currently supported: a championship standings snapshot and a race wins update, both generated manually from existing `DriverStanding` data. Per-race and per-qualifying result notifications are planned once result tables are added.

**Phase 10 — AI Race Assistant**
A protected AI feature for signed-in users. Ask questions about races, drivers, and strategy grounded in real race data.

**Phase 11 — Live Race Dashboard**
A second-screen race dashboard showing the live leaderboard, positions, pit status, tyre compounds, laps remaining, and race control messages.

**Phase 12 — Track Map Visualisation**
A circuit map showing driver positions moving around the track in real time or historical replay.

**Phase 13 — Advanced Analytics**
Tyre strategy visualiser, pit stop comparison, pace charts, driver and team comparisons, and sector analysis.

**Phase 14 — ML Prediction Layer**
Machine learning models for podium prediction, pit window estimation, and race outcome simulation.

---

## Development Notes

- The `.env` file is gitignored and will never be committed. Never hardcode credentials in source files.
- `scripts/create_tables.py` is safe to re-run. It skips tables that already exist.
- `scripts/sync_f1_data.py` is safe to re-run multiple times. It uses upsert logic and will not create duplicate rows.
- `scripts/seed.py` inserts a small hardcoded dataset used during Phase 1 development. It is no longer needed now that `sync_f1_data.py` exists.
- There is no Alembic migration system yet. For model changes, drop the affected tables manually and recreate them with `create_tables.py`.
- Data sync is manual. There is no scheduled or automatic sync yet.
