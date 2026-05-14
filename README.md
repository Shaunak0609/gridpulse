# GridPulse

**F1 Race Intelligence Platform**

GridPulse is a Formula 1 companion app for fans who want to follow races more intelligently. It provides driver and team information, race calendars, standings, and will eventually support live race data, user accounts, notifications, and AI-powered race analysis.

This repository contains the backend API built with Python and FastAPI.

---

## Current Status — Phase 6

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
│   │   ├── reminder.py           # Reminder model (Phase 6)
│   │   └── notification.py       # Notification model (Phase 6)
│   ├── schemas/
│   │   ├── team.py
│   │   ├── driver.py
│   │   ├── race.py
│   │   ├── standing.py
│   │   ├── user.py               # UserCreate, UserLogin, UserResponse, Token
│   │   ├── reminder.py           # ReminderCreate, ReminderResponse (Phase 6)
│   │   └── notification.py       # NotificationResponse (Phase 6)
│   ├── routes/
│   │   ├── auth.py               # POST /auth/signup, POST /auth/login
│   │   ├── google_auth.py        # GET /auth/google/start, GET /auth/google/callback
│   │   ├── users.py              # GET /users/me
│   │   ├── drivers.py
│   │   ├── teams.py
│   │   ├── calendar.py
│   │   ├── standings.py
│   │   ├── reminders.py          # POST/GET/DELETE /reminders (Phase 6)
│   │   └── notifications.py      # GET/PUT/DELETE /notifications (Phase 6)
│   ├── services/
│   │   ├── f1_api_client.py      # HTTP client for Jolpica API
│   │   └── data_ingestion.py     # maps API data into SQLAlchemy models
│   └── main.py
├── frontend/                     # React + Vite + TypeScript frontend (Phase 3)
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

Open `.env` and fill in your database credentials, JWT settings, and Google OAuth credentials:

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
```

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

### Authentication endpoints

| Method | Endpoint | Auth required | Description |
|---|---|---|---|
| POST | `/auth/signup` | No | Create a new user account |
| POST | `/auth/login` | No | Log in and receive a JWT token |
| GET | `/auth/google/start` | No | Redirect browser to Google sign-in |
| GET | `/auth/google/callback` | No | Handle Google redirect, return JWT |
| GET | `/users/me` | Yes — Bearer token | Return the logged-in user's profile |

### Reminder endpoints

All reminder endpoints require a valid JWT Bearer token. Requests without a token return `401`. Requests for another user's reminder return `403`.

| Method | Endpoint | Auth required | Description |
|---|---|---|---|
| POST | `/reminders` | Yes — Bearer token | Create a reminder; also creates a notification |
| GET | `/reminders` | Yes — Bearer token | List the current user's reminders |
| DELETE | `/reminders/{id}` | Yes — Bearer token | Delete a reminder by ID |

### Notification endpoints

All notification endpoints require a valid JWT Bearer token.

| Method | Endpoint | Auth required | Description |
|---|---|---|---|
| GET | `/notifications` | Yes — Bearer token | List the current user's notifications, newest first |
| PUT | `/notifications/{id}/read` | Yes — Bearer token | Mark a notification as read |
| DELETE | `/notifications/{id}` | Yes — Bearer token | Delete a notification by ID |

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

## What Is Not Included Yet

The following features are planned but not yet built:

- Favourite drivers or teams
- Email notifications
- Push notifications
- Scheduled or automatic reminder delivery (the `sent` flag exists but no background job runs yet)
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
