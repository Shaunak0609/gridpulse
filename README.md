# GridPulse

**F1 Race Intelligence Platform**

GridPulse is a Formula 1 companion app for fans who want to follow races more intelligently. It provides driver and team information, race calendars, standings, and will supports historical and near live race data, user accounts, notifications, and AI-powered race analysis.

This repository contains the backend API built with Python and FastAPI.
---

## Link
https://gridpulse-mu.vercel.app/

---

## Current Status — Phase 17

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
| `favorite_driver_standing` | Favourite driver update | After data sync, or via dev endpoint | "Max Verstappen is currently P1 in the 2026 driver standings with 136 points." |
| `favorite_driver_wins` | Race wins update | After data sync, or via dev endpoint, only when wins > 0 | "Max Verstappen has 3 wins in the 2026 season." |

### Phase 9.5 — Automated Notification Scheduling (complete)

- `scripts/sync_f1_data.py` extended — after all F1 data sync steps complete, both notification generators (`generate_standing_notifications` and `generate_wins_notifications`) are called automatically using the same open database session; each generator is wrapped in its own `try/except` so a failure in one does not prevent the other from running
- Sync script output now includes a clear **Favourite Driver Notifications** section after the sync summary, with per-type result blocks showing created, skipped, and email counts
- `POST /notifications/generate-favorite-driver-updates` — new protected development endpoint; requires a valid JWT Bearer token; calls both generators and returns a `NotificationGenerationSummary` JSON response with `users_checked`, `favorite_drivers_checked`, `notifications_created`, and `duplicates_skipped`; documented in `/docs` as a manual/development trigger
- `NotificationGenerationSummary` Pydantic schema added to `app/schemas/notification.py`
- `scripts/generate_favorite_driver_notifications.py` — standalone script is unchanged; continues to work independently for cases where you want to generate notifications without re-running a full data sync
- Duplicate notification prevention is unchanged — both the sync flow and the endpoint rely on the same dedup logic inside each generator

**Normal workflow from Phase 9.5 onwards:**
Running `python scripts/sync_f1_data.py` now handles F1 data refresh and favourite-driver notification generation in a single command.

### Phase 10 — AI Race Assistant (complete)

- `ai_requests` table — stores each user's AI prompt, the assistant's response, model name, token count, and timestamp
- `AIRequest` SQLAlchemy model with a foreign key to `users` and a `user` relationship
- `scripts/migrate_create_ai_requests_table.py` — idempotent migration to create `ai_requests` on an existing database; fresh databases use `create_tables.py` directly
- `app/schemas/ai.py` — three Pydantic schemas: `AIRequestCreate` (prompt + optional request type), `AIResponse` (returned from POST), `AIHistoryResponse` (returned from GET history, includes model name)
- `app/services/ai_service.py` — provider-isolated AI call layer:
  - `AI_PROVIDER`, `AI_API_KEY`, and `AI_MODEL` are read from `.env`
  - Supported providers: `groq` (default, free tier) and `anthropic`
  - Adding a new provider (e.g. OpenRouter) requires only a new `_call_*` function and a one-line entry in `_PROVIDERS`
  - All SDK errors (invalid key, rate limit, credit balance, network) are caught and returned as readable messages rather than raising a 500
- `app/services/ai_context.py` — builds a plain-text context string from the GridPulse database to inject into every prompt:
  - UTC snapshot timestamp (so the AI knows it is not a live feed)
  - User profile, favourite drivers and teams
  - Top-10 driver standings for the configured season
  - Next 5 upcoming sessions
  - Next 3 upcoming reminders
  - Last 3 notifications
  - Explicit "Data NOT Available" section listing race results, qualifying, lap times, pit stops, tyres, and live timing — prevents the AI from inventing those values
- `app/routes/ai.py` — two protected endpoints:
  - `POST /ai/explain` — accepts a prompt, builds context, calls the AI provider, stores the request and response, returns the record; enforces a 20-request-per-user-per-day limit; returns `429` if the limit is reached
  - `GET /ai/history` — returns the current user's last 20 AI requests, newest first
  - `GET /ai/usage` — returns `requests_today`, `daily_limit`, and `remaining` for the current user
- System prompt grounding rules:
  - Three explicit response modes: answer from context, answer from general F1 knowledge (with a disclosure), or say "GridPulse doesn't have that data yet"
  - Prohibition on inventing race results, qualifying times, or lap data
  - Prohibition on inferring race results from championship points
  - Prohibition on using "currently" or "live" language about race events
  - The AI is not permitted to say it is "checking" or "fetching" data — it only has the injected context
- Frontend AI API functions in `api.ts`: `askAI`, `getAIHistory`, `getAIUsage`
- Frontend TypeScript types: `AIResponse`, `AIHistoryItem`, `AIUsage`
- Frontend `/ai` page — protected route; redirects to `/login` if not authenticated:
  - Prompt textarea with ⌘+Enter shortcut and character count
  - Submit button with spinner and "Analysing…" loading state
  - Usage bar showing requests used today out of 20 (colour-coded: green → amber → red)
  - Amber "Daily limit reached" warning when limit is hit; submit button disabled
  - Latest response card with `whitespace-pre-wrap` formatting and timestamp
  - Collapsible question history showing the 20 most recent prompts; click any to expand the full response
  - Empty states for both the response area and history list
- Navbar — "AI" link added to the authenticated link group; not visible when logged out

**AI environment variables (add to `.env`):**

```
AI_PROVIDER=groq
AI_API_KEY=gsk_your_groq_api_key_here
AI_MODEL=llama-3.1-8b-instant
```

`AI_PROVIDER` — `groq` (default, free tier) or `anthropic`.
`AI_API_KEY` — your API key from [console.groq.com](https://console.groq.com) or [console.anthropic.com](https://console.anthropic.com).
`AI_MODEL` — model name for the chosen provider. For Groq: `llama-3.1-8b-instant` (fast, free) or `llama-3.3-70b-versatile` (higher quality). For Anthropic: `claude-haiku-4-5-20251001` or `claude-sonnet-4-6`.

### Phase 11 — OpenF1 / FastF1 Historical Data Upgrade (complete)

Phase 11 adds historical session data to GridPulse using the OpenF1 public API. Laps, stints, race control messages, and weather samples are fetched, stored in PostgreSQL, served via REST endpoints, displayed in a dedicated session detail page, and made available as summarised context for the AI assistant.

**What Phase 11 added:**

- `app/services/openf1_client.py` — HTTP client for the OpenF1 public API (`api.openf1.org/v1`). Functions: `fetch_meetings`, `fetch_sessions`, `fetch_session`, `fetch_drivers`, `fetch_laps`, `fetch_stints`, `fetch_pit_stops`, `fetch_race_control`, `fetch_weather`. A shared `_get(path, params)` helper handles all requests with a 30 s timeout. `BASE_URL` is configurable via the `OPENF1_BASE_URL` environment variable.

- `sessions` table extended with OpenF1 link fields: `openf1_session_key`, `openf1_meeting_key`, `circuit_short_name`, `country_name`. A partial unique index prevents duplicate keys (`WHERE openf1_session_key IS NOT NULL`).

- Four new historical data models and tables:

  | Model | Table | Key fields |
  |---|---|---|
  | `Lap` | `laps` | `session_id`, `driver_number`, `lap_number`, `lap_duration`, `duration_sector_1/2/3`, `is_pit_out_lap`, `date_start` |
  | `Stint` | `stints` | `session_id`, `driver_number`, `stint_number`, `compound`, `lap_start`, `lap_end`, `tyre_age_at_start` |
  | `RaceControlMessage` | `race_control_messages` | `session_id`, `date`, `lap_number`, `category`, `message`, `flag`, `scope`, `sector`, `driver_number` |
  | `WeatherSample` | `weather_samples` | `session_id`, `date`, `air_temperature`, `track_temperature`, `humidity`, `rainfall`, `wind_speed`, `wind_direction` |

- Pydantic response schemas: `LapResponse`, `StintResponse`, `RaceControlMessageResponse`, `WeatherSampleResponse`, `SessionDetailResponse` (includes `race_name`, `circuit_short_name`, `country_name`, `openf1_session_key`).

- `app/services/openf1_ingestion.py` — five ingestion functions:
  - `link_session(session_key, db)` — fetches OpenF1 session metadata, maps session name to our internal type (e.g. "Practice 1" → "fp1"), finds the matching race by date proximity (4-day window), and writes the OpenF1 identifiers into the local session row
  - `ingest_laps(session_id, session_key, db)` — bulk-inserts laps, skipping existing `(driver_number, lap_number)` pairs
  - `ingest_stints(session_id, session_key, db)` — bulk-inserts stints, skipping existing `(driver_number, stint_number)` pairs
  - `ingest_race_control(session_id, session_key, db)` — deletes all existing messages for the session and reinserts from OpenF1 (no reliable unique key exists)
  - `ingest_weather(session_id, session_key, db)` — bulk-inserts samples, skipping existing timestamps. Converts OpenF1's integer rainfall (0/1) to Python bool.

- `scripts/sync_openf1_session.py` — CLI sync script with two modes:
  - `--list YEAR` — prints all OpenF1 sessions for the given year with session key, name, circuit, and date
  - `--session-key KEY` — runs all five ingestion steps for one session and prints inserted/skipped counts

- Five new backend endpoints (public, no auth required):

  | Method | Endpoint | Description |
  |---|---|---|
  | GET | `/sessions/{session_id}` | Single session with race name and OpenF1 link metadata |
  | GET | `/sessions/{session_id}/laps` | All laps, ordered by driver number then lap number |
  | GET | `/sessions/{session_id}/stints` | All stints, ordered by driver number then lap start |
  | GET | `/sessions/{session_id}/race-control` | All race control messages, ordered by timestamp |
  | GET | `/sessions/{session_id}/weather` | All weather samples, ordered by timestamp |

- Frontend `/sessions/:id` page — public route; displays four data sections for a synced session:
  - **Laps** — driver summary table: lap count, fastest lap time (pit-out laps excluded), pit-out count
  - **Stints** — flat table with colour-coded compound badges (SOFT/MEDIUM/HARD/INTERMEDIATE/WET)
  - **Race Control** — chronological message list with lap number and flag badges
  - **Weather** — summary stats (temp range, rain, readings count) plus scrollable readings table
  - All sections show a "No data synced yet" empty state until the sync script is run
  - Header shows "Data synced" / "Not synced" badge based on `openf1_session_key`

- Calendar page updated — past session names are now clickable links to `/sessions/:id`.

- `app/services/ai_context.py` updated — includes historical data summaries for the last 3 synced sessions:
  - Lap count and number of drivers (aggregate only — no raw rows dumped)
  - Tyre/stint summary: total stints with compound breakdown (e.g. "40 stints — 16×SOFT, 14×MEDIUM, 10×HARD")
  - Weather summary: air and track temperature range, rain status, reading count
  - Last 6 race control messages verbatim, with lap number and flag
  - Explicit "no data synced" message if no sessions have been linked yet
  - "Data NOT Available" section updated: lap times, tyre data, and weather are now noted as stored-but-summarised; pit stop durations, live timing, and FastF1 telemetry remain absent

- Migration scripts:
  - `scripts/migrate_add_openf1_session_fields.py` — adds the four OpenF1 columns to the existing sessions table
  - `scripts/migrate_create_openf1_tables.py` — creates the four new historical data tables

**FastF1 planning:**
FastF1 is a Python library providing car telemetry (speed, throttle, brake, RPM, gear, DRS) and GPS position data that OpenF1 does not offer. Integration is planned for a later phase when track map and advanced analytics features are ready. FastF1 is not used in Phase 11 — OpenF1 covers all Phase 11 requirements via REST. See the FastF1 planning notes below.

### Phase 12 — Historical Race Dashboard (complete)

Phase 12 adds a structured per-session dashboard built entirely from stored OpenF1 historical data. It surfaces lap counts, a derived finishing order, tyre strategy, race control events, and weather in a single page. Favourite drivers are highlighted for logged-in users. The AI context builder was refactored to use the same data layer and given explicit missing-data awareness.

**What Phase 12 added:**

- `app/services/session_dashboard.py` — single source of truth for building a `SessionDashboardSummary` from the database. All heavy work (lap aggregation, finishing order derivation, stint grouping, RC message curation, weather latest-sample selection) lives here. Used by both the API endpoint and the AI context builder — no duplicate queries.

- `app/schemas/session_dashboard.py` — Pydantic response models that mirror the service dataclasses:

  | Schema | Description |
  |---|---|
  | `DashboardLapStats` | Total lap rows, driver count, max lap number |
  | `DashboardDriverSummary` | Position, driver number/name, max lap, laps behind, is_favourite flag |
  | `DashboardStintEntry` | Stint number, compound, lap range, tyre age at start |
  | `DashboardStintSummary` | All stints for one driver, is_favourite flag |
  | `DashboardKeyEvent` | Label and lap number for notable RC events (safety car, red flag, DRS…) |
  | `DashboardRCMessage` | Lap number, flag, and message text for one curated RC entry |
  | `DashboardRaceControlSummary` | Key events list, curated message list, counts |
  | `DashboardLatestWeatherSample` | Air/track temp, humidity, rainfall, wind speed/direction |
  | `DashboardWeatherSummary` | Session range stats plus the latest reading |
  | `SessionDashboardResponse` | Top-level response; exposes all sections plus has_* availability flags |

- `GET /sessions/{session_id}/dashboard` — new public endpoint (optional JWT). Returns a `SessionDashboardResponse` for the session. Returns `404` if the session does not exist. Accepts an optional Bearer token; if provided and valid, `is_favourite` flags on driver rows reflect the authenticated user's favourites. If no token is provided, `is_favourite` is always `false`.

- `get_optional_user` dependency (`app/auth/dependencies.py`) — returns `User | None`, never raises. Used by the dashboard endpoint so anonymous callers receive a valid response without authentication errors.

- `GET /sessions/synced` — returns all sessions that have been linked to an OpenF1 session key, ordered by start time descending. Used by the frontend to populate the session picker.

- Frontend `getSessionDashboard(sessionId, token?)` in `api.ts` — fetches the dashboard endpoint. Passes the JWT as a Bearer token if the user is logged in, so `is_favourite` flags are populated.

- Frontend `/sessions/:id/dashboard` page (`SessionDashboard.tsx`):
  - Public route — accessible without login; personal favourite highlighting appears for logged-in users only
  - Waits for `authLoading` to resolve before fetching, preventing an anonymous request followed immediately by an authenticated one
  - Declared before `/sessions/:id` in `App.tsx` to avoid route conflict

- **Dashboard sections:**

  | Section | Contents | Shown when |
  |---|---|---|
  | Session summary | Race name, circuit, country, date, sync status | Always |
  | Lap summary | Total lap rows, distinct driver count, max lap number | `has_lap_data = true` |
  | Finishing order | Derived leaderboard sorted by max lap then final-lap timing | Race and sprint sessions with lap data |
  | Tyre strategy | Compound overview + per-driver stint pills (S1 / S2 / S3) | `has_stint_data = true` |
  | Race control | Key events (safety car, red flag, VSC, DRS, penalties) + curated message list | `has_rc_data = true` |
  | Weather | Latest reading (air temp, track temp, humidity, wind) + session range | `has_weather_data = true` |

- **Empty states:** each section shows a specific message when its `has_*` flag is false — e.g. "No lap data has been synced for this session yet." A page-level footnote explains the OpenF1 sync dependency.

- **Favourite driver highlighting:** drivers marked `is_favourite = true` receive a red star (★) in the finishing order and tyre strategy tables, and a subtle red row tint. Logged-out users see no highlighting.

- **Calendar navigation:** past session rows on the Calendar page show a "Dashboard →" link that opens `/sessions/:id/dashboard`.

**AI context improvements:**

- `ai_context.py` refactored — `_session_block()` now calls `build_session_summary()` instead of running duplicate DB queries. The six private helper functions that existed only to replicate session_dashboard logic were removed.

- **Missing-data flags** — every session block now includes a `Missing: no_lap_data, no_stint_data, no_race_control_data, no_weather_data` line for any section that has not been synced. The AI reads these before answering and states what is absent rather than guessing.

- **Per-driver lap table** — for qualifying and FP sessions (where there is no finishing order), the context includes a compact table of max lap numbers per driver so the AI can answer "how many laps did [driver] complete in qualifying?".

- **Latest weather reading** — the AI context now includes the most recent weather sample (air temperature, track temperature, humidity, wind speed and direction) alongside the existing session-range stats.

- **Token budget safeguards** — three AI-specific caps protect the Groq free-tier 6 000 TPM limit:
  - `_MAX_SYNCED_SESSIONS = 2` (session blocks included in context)
  - `_AI_MAX_RC = 15` (RC messages per session; service-level cap is 40)
  - `_AI_MAX_DRIVER_LAPS = 10` (per-driver rows in qualifying/FP lap table)
  - System prompt trimmed to ~621 tokens; total worst-case request is ~3 800 tokens

**What the AI can answer from dashboard data:**
- Approximate finishing order for synced race and sprint sessions ("based on synced lap data")
- Tyre compounds, lap ranges, and whether tyres were new or used for any driver in a synced session
- Key race events (safety car deployments, red flags, DRS openings, penalties) with lap numbers
- Curated race control messages for specific laps or incident queries
- Session weather: temperature range, rainfall, humidity, wind direction
- How many laps a driver completed (race/sprint from finishing order; qualifying/FP from per-driver lap table)

**What the AI still cannot answer if data is missing:**
- Anything flagged `no_lap_data`, `no_stint_data`, `no_race_control_data`, or `no_weather_data` — the AI states exactly which data is absent and does not guess
- Official race classifications — the finishing order is derived from lap timing; post-race penalties and disqualifications are not reflected
- Qualifying results, grid positions, or pole lap times — no `qualifying_results` table exists
- Individual lap times per driver or fastest lap records
- Pit stop durations or exact pit window timing

**How to sync data before using the dashboard:**

1. Find the OpenF1 session key for the session you want:
   ```bash
   python scripts/sync_openf1_session.py --list 2024
   ```
2. Sync it:
   ```bash
   python scripts/sync_openf1_session.py --session-key 9158
   ```
3. Open the Calendar page, expand the race, and click **Dashboard →** on the session row.

### Phase 13 — Strategy Dashboard (complete)

Phase 13 adds a dedicated strategy page built entirely from stored OpenF1 historical data. It organises tyre compound usage, per-driver stint sequences, pit windows, strategy-relevant race control events, and weather into a single readable page — with rule-based insights derived purely from stored data. No ML, no live timing.

**What Phase 13 added:**

- `app/services/strategy_dashboard.py` — new strategy service. Single source of truth for all strategy data, used by both the API endpoint and the AI context builder:
  - `build_strategy_summary(session, db, current_user)` — computes compound usage, stop counts, pit windows, per-driver compound sequences, wet-tyre detection, and rule-based insights
  - Pit windows are derived by clustering `lap_start` values of 2nd+ stints per driver, grouping events within a ±6-lap gap
  - Strategy-relevant RC filter: excludes BLUE flag messages; includes YELLOW, DOUBLE YELLOW, RED, SAFETY CAR flags and keywords VSC, RED FLAG, PIT LANE, RISK OF RAIN, WEATHER, MEDICAL CAR, RETIRED
  - `format_strategy_context_lines(summary)` — compact text output for AI context integration (not used directly; `_ai_strategy_lines()` in `ai_context.py` produces a tailored subset)

- `app/schemas/strategy_dashboard.py` — Pydantic response models and `from_summary()` converter:

  | Schema | Description |
  |---|---|
  | `StrategyCompoundUsage` | Compound name, stint count, driver count, average stint length |
  | `StrategyStintSummary` | Stint number, compound, lap range, tyre age, derived lap count |
  | `StrategyDriverSummary` | All strategy data for one driver; `stop_count`, `compound_sequence`, `longest_stint_laps`, `is_favourite` |
  | `StrategyPitWindow` | 1-based window number, earliest and latest pit lap, driver count |
  | `StrategyRCEvent` | Lap number, flag, message for one strategy-relevant RC entry |
  | `StrategyRaceControlContext` | Filtered RC events and total count |
  | `StrategyWeatherContext` | Rain status, wet-tyre driver list, air/track temperature range, latest reading |
  | `StrategyDashboardResponse` | Top-level response; all sections plus `has_*` availability flags and a `insights` string list |

- `GET /sessions/{session_id}/strategy` — new endpoint added to `sessions.py`. Public with optional Bearer token for favourite-driver highlighting. Returns `404` if the session does not exist. Uses `get_optional_user` so unauthenticated callers receive a valid response without authentication errors. Route declared before `/sessions/{session_id}` to avoid path collision.

- Frontend `getSessionStrategy(sessionId, token?)` in `api.ts` — fetches the strategy endpoint. Passes the JWT as a Bearer token if the user is logged in so `is_favourite` flags are populated.

- Frontend `/sessions/:id/strategy` page (`StrategyDashboard.tsx`):
  - Public route — accessible without login; favourite-driver highlighting appears for logged-in users only
  - Waits for `authLoading` to resolve before fetching, preventing an unauthenticated request followed by an authenticated one
  - Declared before `/sessions/:id` in `App.tsx` to avoid React Router treating "strategy" as a session ID

- **Strategy Dashboard sections:**

  | Section | Contents | Shown when |
  |---|---|---|
  | Session summary | Race name, circuit, country, date, sync status | Always |
  | Strategy insights | Rule-based sentences derived from stored data | `has_stint_data = true` |
  | Compound usage | Cards per compound: stint count, driver count, average stint length | `has_stint_data = true` |
  | Driver strategies | Per-driver cards with compound sequence, stop count, stint table, longest-stint highlight | `has_stint_data = true` |
  | Stop count groups | Drivers grouped by number of pit stops | `has_stint_data = true` |
  | Pit windows | Table of clustered pit lap ranges with an approximation disclaimer | `has_stint_data = true` and stop data available |
  | Race control | Strategy-relevant events with per-event cautious context notes | `has_rc_data = true` |
  | Weather | Session range (air/track min–max, rainfall) + latest reading (temp, humidity, wind) | `has_weather_data = true` |

- **Rule-based insights** — `_generate_insights()` produces up to nine plain-English sentences from pre-computed data. No ML, no predictions:
  1. Data completeness warning if >30% of stints are missing lap ranges
  2. Most-used compound with average stint length
  3. Driver with the most stints (or multiple drivers if tied)
  4. Driver and compound for the longest single stint
  5. Multi-compound vs single-compound driver split
  6. Named single-compound drivers (when ≤5)
  7. Wet-weather tyre usage by driver name
  8. Rain recorded with no wet-tyre compound data (data gap note)
  9. Track temperature variance ≥10°C (cautious wording)

- **Favourite-driver highlighting:** drivers with `is_favourite = true` are sorted to the top of the driver strategies list, shown with a red border and a ★ star. The longest stint for each driver is highlighted in amber in their stint table.

- **Empty states:** each section shows a specific message when its `has_*` flag is false. A page-level footnote explains the OpenF1 sync dependency.

- **Navigation links:**
  - Calendar page — past session rows now show "Dashboard →" and "Strategy →" links stacked vertically in the same column
  - Session Dashboard nav bar — "Strategy →" link added alongside the existing "Raw data →" and "← Calendar" links

**AI context improvements:**

- `app/services/ai_service.py` — system prompt updated with a STRATEGY section. The model is explicitly told to: use only stored stint data; never invent pit stops, compound choices, undercuts, or overcuts; reference the per-driver compound sequences for "What tyres did X run?" questions; use stop counts for "How many stops?" questions; say "GridPulse does not have enough synced stint data to answer that" when `no_stint_data` is flagged.

- `app/services/ai_context.py` — the verbose per-driver stint block in `_session_block()` is replaced by `_ai_strategy_lines()`, a new helper that:
  - Calls `build_strategy_summary()` — consistent with what the strategy endpoint and page use
  - Emits compact compound usage, stop-count totals (counts only, not driver name lists), pit windows, and per-driver compound sequences capped at `_AI_MAX_STRATEGY_DRIVERS = 20`
  - Includes up to `_AI_MAX_INSIGHTS = 4` rule-based insight sentences
  - Does not duplicate RC events or weather — those are covered by the existing blocks in `_session_block()`

**Token budget safeguards:**

| Cap | Value | Purpose |
|---|---|---|
| `_MAX_SYNCED_SESSIONS` | 2 | Session blocks included in the AI context |
| `_AI_MAX_RC` | 15 | RC messages per session (service-level cap is 25) |
| `_AI_MAX_DRIVER_LAPS` | 10 | Per-driver rows in qualifying/FP lap table |
| `_AI_MAX_STRATEGY_DRIVERS` | 20 | Per-driver strategy rows per session |
| `_AI_MAX_INSIGHTS` | 4 | Rule-based insight sentences per session |

**What the AI can answer from strategy data:**
- Tyre compound breakdown for a synced session (most used compound, stint counts, average stint length)
- Total pit stop counts per group ("19 drivers made 1 stop, 2 made 2 stops")
- Approximate pit window lap ranges derived from stint transitions
- Per-driver compound sequences ("Verstappen ran MEDIUM → HARD with 1 stop, longest stint 31 laps")
- Driver with the longest single stint and the compound used
- Rule-based insights derived from stored data

**What the AI still cannot answer if data is missing:**
- Anything flagged `no_stint_data` — the AI states exactly what is absent and does not guess
- Exact pit stop timing or official pit durations — pit windows are derived from stint transitions, not official timing
- Undercuts, overcuts, and strategic decisions — the AI is explicitly instructed not to make these inferences
- Official finishing order or post-race classifications
- Individual lap times or sector times per driver
- Qualifying grid positions or pole times

**How to sync data before using the Strategy Dashboard:**

The Strategy Dashboard requires OpenF1 data for the session to be synced first. Without it, all sections show empty states with `has_* = false`.

1. Find the OpenF1 session key:
   ```bash
   python scripts/sync_openf1_session.py --list 2026
   ```
2. Sync the session:
   ```bash
   python scripts/sync_openf1_session.py --session-key <key>
   ```
3. Open the Calendar page and click **Strategy →** on any past session row, or navigate directly to `/sessions/:id/strategy`.

### Phase 14 — Advanced Analytics (complete)

Phase 14 adds a dedicated analytics page built entirely from stored OpenF1 historical data. It computes and displays per-driver pace, compound performance, teammate comparisons, race control context, and weather — with Recharts visualisations and a side-by-side driver comparison tool. The AI context builder was updated to include analytics summaries so the assistant can answer pace-based questions.

**What Phase 14 added:**

- `app/services/analytics_service.py` — analytics computation layer. Single source of truth for all pace and performance data, used by both the API endpoints and the AI context builder:
  - `build_session_analytics(session, db, current_user)` — computes per-driver fastest and average lap times, compound pace averages, teammate comparisons, safety car and red flag lap lists, and latest weather
  - `compare_drivers(summary, driver_a, driver_b)` — returns a side-by-side comparison from pre-computed data, with delta values in seconds (negative = driver A faster)
  - `get_session_analytics(session_id, db, current_user)` — fetches the session and builds the full summary; returns `None` if not found
  - `_MIN_LAPS_FOR_AVERAGE = 3` — minimum timed laps before reporting an average (prevents noise from partial sessions)
  - All pace calculations exclude `is_pit_out_lap = True` laps

- `app/schemas/analytics.py` — Pydantic response models:

  | Schema | Description |
  |---|---|
  | `DriverAnalyticsSummary` | Driver number, name, lap count, timed lap count, fastest lap, average lap, best sectors, `is_favourite` flag |
  | `AnalyticsCompoundUsage` | Compound name, average and fastest lap time, driver count, sample lap count |
  | `AnalyticsStintEntry` | Stint with driver, compound, lap range, average lap time, laps counted |
  | `AnalyticsTireSummary` | Compound pace list, stint pace list, `has_compound_pace` flag |
  | `TeammateComparisonSummary` | Team name, two drivers with fastest and average times, fastest and average delta (seconds) |
  | `AnalyticsRaceContext` | Total RC message count, safety car lap list, red flag lap list |
  | `AnalyticsWeatherSummary` | Air temperature, track temperature, humidity, rainfall, wind speed |
  | `SessionAnalyticsResponse` | Top-level response; all sections plus `has_*` availability flags |
  | `DriverComparisonResponse` | Two driver summaries with deltas and per-driver stint lists |

- Three new analytics endpoints (all public with optional Bearer token for `is_favourite` highlighting):

  | Method | Endpoint | Description |
  |---|---|---|
  | GET | `/analytics/sessions/{session_id}` | Full analytics summary — session pace, per-driver stats, compound averages, teammate comparisons, race context, weather |
  | GET | `/analytics/sessions/{session_id}/compare` | Side-by-side comparison of two drivers; `?driver1=4&driver2=1` query params; `404` with a list of valid car numbers if a driver is not found |
  | GET | `/analytics/sessions/{session_id}/tires` | Tire analytics only — compound pace averages and per-stint pace |

- `app/routes/analytics.py` — analytics router with prefix `/analytics`, registered in `app/main.py`

- Nine new TypeScript interfaces in `types/index.ts`: `AnalyticsDriverSummary`, `AnalyticsCompoundUsage`, `AnalyticsStintEntry`, `AnalyticsTireSummary`, `AnalyticsTeammateComparison`, `AnalyticsRaceContext`, `AnalyticsWeather`, `SessionAnalytics`, `DriverComparisonAnalytics`

- Frontend analytics API functions in `api.ts`: `getSessionAnalytics`, `compareSessionDrivers`, `getSessionTireAnalytics`

- Frontend `/sessions/:id/analytics` page (`AnalyticsDashboard.tsx`):
  - Public route — accessible without login; favourite-driver highlighting appears for logged-in users only
  - Both main analytics and tire analytics endpoints fetched in parallel via `Promise.all`
  - Declared before `/sessions/:id` in `App.tsx` to avoid React Router treating "analytics" as a session ID

- **Analytics page sections:**

  | Section | Contents | Shown when |
  |---|---|---|
  | Session summary | Race name, circuit, country, date, sync status | Always |
  | Session pace | Session fastest lap and driver, session average | `has_lap_data = true` |
  | Driver pace table | Per-driver fastest and average lap, best sectors, lap count, `is_favourite` star | `has_lap_data = true` |
  | Compound pace | Average and fastest lap per compound, driver count, sample lap count | `has_stint_data = true` and `has_compound_pace = true` |
  | Teammate comparisons | Side-by-side delta for each pair of teammates on the same team | `has_lap_data = true` and team data available |
  | Race control context | Total RC messages, safety car laps, red flag laps | `has_rc_data = true` |
  | Weather | Air/track temp, humidity, rainfall, wind | `has_weather_data = true` |

- **Recharts visualisations** — three bar charts using `recharts@3.x`:
  - **Lap count chart** — horizontal bar chart of total laps per driver; bars coloured red for favourites, grey for others
  - **Fastest lap gap chart** — horizontal bar chart showing each driver's gap to the session fastest lap in seconds; the fastest driver's bar is shown at reduced opacity to make it visually distinct
  - **Compound usage chart** — vertical bar chart with compounds ordered `SOFT → MEDIUM → HARD → INTERMEDIATE → WET`; coloured per compound
  - All charts use `ResponsiveContainer` and a custom dark-themed `ChartTooltip`

- **Driver comparison tool:** select any two car numbers from dropdowns, click **Compare**, and see a side-by-side card with fastest lap, average lap, deltas (negative = driver A faster), and per-driver stint tables with compound and lap range; shows an empty state if fewer than two drivers have lap data

- **Three-level compound empty state:**
  - `!has_stint_data` → "No stint/tire data has been synced for this session yet."
  - `has_stint_data && !has_compound_pace` → "Compound pace requires stints with lap ranges stored. The stints for this session were synced without `lap_start` / `lap_end`, so per-compound averages cannot be computed."
  - Both flags true but no data → "No compound pace data available."

- **Navigation links:**
  - Calendar page — past session rows now show three stacked links: **Dashboard →**, **Strategy →**, **Analytics →** (purple hover)
  - Session Dashboard nav bar — **Analytics →** link added alongside Strategy and Raw data links
  - Strategy Dashboard nav bar — **Analytics →** link added alongside Session dashboard link

**AI context improvements:**

- `app/services/ai_context.py` — added `_ai_analytics_lines()` function, called inside `_session_block()` before the strategy block. Produces a compact analytics block with token safeguards:
  - Returns `[]` when `has_lap_data` is false (avoids a redundant missing-data message since `_session_block()` already emits `Missing: no_lap_data`)
  - Emits session fastest and average, per-driver fastest and average (capped at `_AI_MAX_ANALYTICS_DRIVERS = 20`)
  - Compound pace averages with sample lap counts (when `has_compound_pace = true`)
  - Safety car laps (up to 8) and red flag laps (up to 5) with a caveat that those lap times are not race pace
  - Wrapped in `try/except` — any analytics service failure returns `[]` silently

- `app/services/ai_service.py` — system prompt updated with an ANALYTICS section:
  - "Who was fastest?" → session fastest lap and per-driver pace list
  - "What was X's lap time / average pace?" → per-driver pace entries
  - "Which compound was fastest?" → compound pace averages
  - "Were there safety cars?" → safety car laps list
  - If `no_lap_data`: say "GridPulse does not have enough synced lap data to answer that yet."
  - If team mapping is unavailable: say "GridPulse does not have reliable driver-to-team mapping for this session."
  - Updated WHAT GRIDPULSE DOES NOT HAVE: replaced "individual lap times per driver" with "full per-lap time sequences (only fastest, average, and sector best times are available per driver via the Analytics section)"

**Token budget safeguards (updated):**

| Cap | Value | Purpose |
|---|---|---|
| `_MAX_SYNCED_SESSIONS` | 2 | Session blocks included in AI context |
| `_AI_MAX_RC` | 15 | RC messages per session |
| `_AI_MAX_DRIVER_LAPS` | 10 | Per-driver rows in qualifying/FP lap table |
| `_AI_MAX_STRATEGY_DRIVERS` | 20 | Per-driver strategy rows per session |
| `_AI_MAX_INSIGHTS` | 4 | Rule-based insight sentences per session |
| `_AI_MAX_ANALYTICS_DRIVERS` | 20 | Per-driver analytics rows per session |

**What the AI can answer from analytics data:**
- Session fastest lap and who set it, with the time in seconds
- Per-driver fastest and average pace for any driver in a synced session
- Compound pace averages with sample lap counts ("SOFT averaged 89.1s across 45 laps")
- Whether there were safety car or red flag laps and which laps they fell on (with a caveat that lap times on those laps are not race pace)

**What the AI still cannot answer if data is missing:**
- Anything flagged `no_lap_data` — the AI says "GridPulse does not have enough synced lap data to answer that yet" and does not guess
- Full per-lap time sequences — only fastest and average times per driver are stored in the analytics summary
- Compound pace if stints lack `lap_start` / `lap_end` ranges — the AI notes that stints were synced without lap ranges
- Official sector bests from timing towers — sector data is from stored OpenF1 lap rows only
- Qualifying times, official race pace, or any live timing data

**How to sync data before using the Analytics Dashboard:**

The Analytics Dashboard requires OpenF1 data for the session to be synced first. Without it, all sections show empty states with `has_* = false`.

1. Find the OpenF1 session key:
   ```bash
   python scripts/sync_openf1_session.py --list 2026
   ```
2. Sync the session:
   ```bash
   python scripts/sync_openf1_session.py --session-key <key>
   ```
3. Open the Calendar page and click **Analytics →** on any past session row, or navigate directly to `/sessions/:id/analytics`.

### Phase 15 — Sync-Based Favourite Driver Session Alerts (complete)

Phase 15 adds per-session alert detection for favourited drivers. **These are not live alerts** — they are generated from stored OpenF1 historical data after a session is synced. The system reads lap, stint, and race control records to detect events involving a user's favourited drivers, then creates in-app notifications (and optional emails) for each affected user.

**What Phase 15 added:**

- `app/services/favorite_driver_alerts.py` — alert detection service. Four independent detectors run per driver per session:
  - `_detect_fastest_lap` — fires when the driver holds the session's `MIN(lap_duration)` (pit-out laps excluded); uses a 0.001 s tolerance for floating-point ties
  - `_detect_strategy` — fires when any stint record exists for the driver; summarises compound sequence, stop count, and longest stint
  - `_detect_rc_mention` — fires when any `race_control_messages` row has `driver_number` matching the driver's car number (structured column only — no text search)
  - `_detect_lap_comparison` — fires only for race/sprint sessions when the driver's `MAX(lap_number)` is ≥ 4 less than the session maximum; uses cautious language and explicitly states no official retirement data is stored

- `app/models/notification.py` updated — `related_session_id` nullable FK (`INTEGER REFERENCES sessions(id) ON DELETE SET NULL`) added; `related_session` relationship added

- `app/schemas/notification.py` updated — `related_session_id: int | None` added to `NotificationResponse`

- `app/schemas/alert.py` — two new Pydantic schemas: `AlertTypeResult` (created, skipped, emails_sent, emails_failed per type) and `SessionAlertGenerationResult` (session identity, is_synced flag, per-type breakdown, totals)

- `scripts/migrate_add_notification_session_id.py` — idempotent migration; adds `related_session_id` to an existing `notifications` table using `ADD COLUMN IF NOT EXISTS`

- `scripts/generate_favorite_driver_alerts.py` — CLI alert generation script:

  ```bash
  # List all synced sessions with their GridPulse session IDs
  python scripts/generate_favorite_driver_alerts.py --list

  # Generate alerts for one session
  python scripts/generate_favorite_driver_alerts.py --session-id 5
  ```

  Output shows per-type created/skipped/email counts and a psql tip when all alerts already exist.

- `POST /notifications/generate-favorite-driver-alerts/{session_id}` — protected development endpoint; requires a valid Bearer token; runs all four detectors for the session and returns a `SessionAlertGenerationResult` JSON response; returns `404` if the session does not exist or has not been synced

- Email delivery — after each new alert notification is committed, an email is sent if the user has both `email_notifications_enabled` and `favorite_driver_email_alerts_enabled` set to `true`; the notification row is always saved first so in-app delivery is never lost even if the email call fails

- Frontend Notifications page (`/notifications`) — new type-specific icons and colour-coded badges for all notification types; session alert types receive distinct visual treatment:

  | Type | Icon | Badge colour |
  |---|---|---|
  | `favorite_driver_fastest_lap` | Bolt / lightning | Purple |
  | `favorite_driver_strategy` | Tyre (concentric circles) | Orange |
  | `favorite_driver_rc_mention` | Flag | Yellow |
  | `favorite_driver_lap_comparison` | Warning triangle | Slate |
  | `favorite_driver_standing` / `wins` | Filled star | Amber |
  | `reminder_created` | Bell | Blue |

- Frontend Dashboard page — "Driver Updates" section expanded from 2 to all 6 `favorite_driver_*` types; type-appropriate icons and small type badge labels added per card; slice increased to 4 items

- Frontend Session Dashboard (`/sessions/:id/dashboard`) — compact "Your Driver Alerts" panel (max 3 entries, link to `/notifications`) fetches notifications from the API and filters to `related_session_id === sessionId` and `type.startsWith('favorite_driver_')`; fails silently so page still works when unauthenticated or when no alerts exist

- Frontend Strategy Dashboard (`/sessions/:id/strategy`) — compact "Your Strategy Alerts" panel filters to `type === 'favorite_driver_strategy'` for the session; rendered with orange tire icon; positioned after the no-stint-data notice and before the insights section

- AI context update (`ai_context.py`) — new "Favourite-Driver Alerts" section (up to `_MAX_DRIVER_ALERTS = 5` entries, most recent first) injected before the driver number reference. Each entry includes: type label, driver name, session label, data source, read/unread status, and the full pre-computed alert message. The existing "Recent Notifications" section now excludes `favorite_driver_*` types so they are not double-counted.

- AI system prompt update (`ai_service.py`) — new `== FAVOURITE-DRIVER ALERTS ==` section with explicit routing rules:
  - Tyre change questions → only answer if a strategy alert or stint data exists
  - Position gain/loss questions → state that GridPulse has no per-lap position column
  - Investigation/penalty questions → only answer from rc_mention alert or RC messages (no text search)
  - Retirement/DNF questions → quote the lap comparison alert; always add the no-official-classification disclaimer; never speculate on cause
  - Missing data → name exactly which data source is absent

**Supported alert types and their data sources:**

| Alert type | Fires when | Source table | Supported for |
|---|---|---|---|
| `favorite_driver_fastest_lap` | Driver holds session `MIN(lap_duration)` | `laps` | All synced sessions |
| `favorite_driver_strategy` | Any stint row exists for the driver | `stints` | All synced sessions |
| `favorite_driver_rc_mention` | Any RC row has `driver_number` matching the driver | `race_control_messages` | All synced sessions |
| `favorite_driver_lap_comparison` | Driver completed ≥4 fewer laps than session max | `laps` | Race and sprint sessions only |

**Dedup:** One notification per `(user_id, type, related_driver_id, related_session_id)`. Running the script or endpoint more than once for the same session is safe — existing alerts are counted as skipped, not duplicated.

**When alerts are generated:**

Alerts are not generated automatically. The recommended workflow is:

1. Sync a session: `python scripts/sync_openf1_session.py --session-key <key>`
2. Generate alerts: `python scripts/generate_favorite_driver_alerts.py --session-id <id>`

Alternatively, trigger via the API endpoint after syncing.

---

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
| External data | Jolpica F1 API, OpenF1 API |
| HTTP client | requests |
| Environment | python-dotenv |
| Password hashing | passlib + bcrypt |
| JWT tokens | python-jose |
| Google OAuth | google-auth |
| Email delivery | Resend |
| AI provider | Groq (default, free tier) / Anthropic |
| AI SDK | groq / anthropic Python SDKs |
| Frontend | React + Vite + TypeScript |
| Styling | Tailwind CSS v4 |
| Routing | React Router v6 |
| Charts | Recharts |

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

**OpenF1 API** — `https://api.openf1.org/v1`

OpenF1 is a free, public F1 data API with no authentication required. GridPulse uses it to fetch historical session data:

| Data | OpenF1 endpoint |
|---|---|
| Session metadata | `/sessions?session_key={key}` |
| Lap times | `/laps?session_key={key}` |
| Stint and tyre data | `/stints?session_key={key}` |
| Race control messages | `/race_control?session_key={key}` |
| Weather samples | `/weather?session_key={key}` |

Data is fetched manually via the sync script and stored in PostgreSQL. OpenF1 coverage begins from the 2023 season. It does not provide car telemetry (speed, throttle, GPS position) — that requires FastF1, which is planned for a later phase.

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
│   │   ├── notification.py       # Notification model; related_session_id FK added (Phase 6/15)
│   │   ├── session.py            # Session model (Phase 7.5)
│   │   ├── favorite_driver.py    # FavoriteDriver model — user/driver join table (Phase 8)
│   │   ├── favorite_team.py      # FavoriteTeam model — user/team join table (Phase 8)
│   │   ├── ai_request.py         # AIRequest model — stores prompt, response, tokens (Phase 10)
│   │   ├── lap.py                # Lap model — per-driver lap times from OpenF1 (Phase 11)
│   │   ├── stint.py              # Stint model — tyre stint data from OpenF1 (Phase 11)
│   │   ├── race_control_message.py  # RaceControlMessage model — steward/flag messages (Phase 11)
│   │   └── weather_sample.py     # WeatherSample model — trackside weather readings (Phase 11)
│   ├── schemas/
│   │   ├── team.py
│   │   ├── driver.py
│   │   ├── race.py
│   │   ├── standing.py
│   │   ├── user.py               # UserCreate, UserLogin, UserResponse, Token
│   │   ├── reminder.py           # ReminderCreate/Response with optional session_id (Phase 6/7.5)
│   │   ├── notification.py       # NotificationResponse; related_session_id added (Phase 6/15)
│   │   ├── alert.py              # AlertTypeResult, SessionAlertGenerationResult (Phase 15)
│   │   ├── session.py            # SessionCreate, SessionResponse, SessionDetailResponse (Phase 7.5/11)
│   │   ├── favorite.py           # FavoriteDriverResponse, FavoriteTeamResponse + nested info schemas (Phase 8)
│   │   ├── dashboard.py          # DashboardResponse — assembles all sections (Phase 8)
│   │   ├── ai.py                 # AIRequestCreate, AIResponse, AIHistoryResponse (Phase 10)
│   │   ├── lap.py                # LapResponse (Phase 11)
│   │   ├── stint.py              # StintResponse (Phase 11)
│   │   ├── race_control_message.py  # RaceControlMessageResponse (Phase 11)
│   │   ├── weather_sample.py     # WeatherSampleResponse (Phase 11)
│   │   ├── session_dashboard.py  # SessionDashboardResponse and all nested schemas (Phase 12)
│   │   ├── strategy_dashboard.py # StrategyDashboardResponse and nested schemas; from_summary() converter (Phase 13)
│   │   └── analytics.py          # SessionAnalyticsResponse, DriverComparisonResponse, AnalyticsTireSummary and nested schemas (Phase 14)
│   ├── routes/
│   │   ├── auth.py               # POST /auth/signup, POST /auth/login
│   │   ├── google_auth.py        # GET /auth/google/start, GET /auth/google/callback
│   │   ├── users.py              # GET /users/me, email-preferences, notification-preferences (Phase 7/9)
│   │   ├── drivers.py
│   │   ├── teams.py
│   │   ├── calendar.py
│   │   ├── standings.py
│   │   ├── reminders.py          # POST/GET/DELETE /reminders (Phase 6/7.5)
│   │   ├── notifications.py      # GET/PUT/DELETE /notifications + dev generate endpoints (Phase 6/9.5/15)
│   │   ├── email.py              # POST /email/test, POST /email/send-due-reminders (Phase 7)
│   │   ├── sessions.py           # GET /sessions/upcoming, /synced, /races/{id}/sessions, /sessions/{id}, dashboard + strategy endpoints (Phase 7.5/11/12/13)
│   │   ├── favorites.py          # GET/POST/DELETE /me/favorites/drivers + /teams (Phase 8)
│   │   ├── dashboard.py          # GET /me/dashboard (Phase 8)
│   │   ├── ai.py                 # POST /ai/explain, GET /ai/history, GET /ai/usage (Phase 10)
│   │   └── analytics.py          # GET /analytics/sessions/{id}, /compare, /tires (Phase 14)
│   ├── services/
│   │   ├── f1_api_client.py      # HTTP client for Jolpica API
│   │   ├── data_ingestion.py     # maps API data into SQLAlchemy models
│   │   ├── email_service.py      # Resend wrapper (Phase 7)
│   │   ├── reminder_email_service.py  # due-reminder delivery; session-aware email body (Phase 7/7.5)
│   │   ├── favorite_driver_notifications.py  # standing + wins notification generators (Phase 9)
│   │   ├── favorite_driver_alerts.py         # session alert detectors: fastest_lap, strategy, rc_mention, lap_comparison (Phase 15)
│   │   ├── ai_service.py         # provider-isolated AI call layer; Groq + Anthropic; alert-aware system prompt (Phase 10/13/15)
│   │   ├── ai_context.py         # builds plain-text GridPulse context for AI prompts; includes alert section (Phase 10/11/12/13/15)
│   │   ├── openf1_client.py      # HTTP client for OpenF1 API — fetch_laps, fetch_stints, fetch_race_control, fetch_weather, etc. (Phase 11)
│   │   ├── openf1_ingestion.py   # link_session, ingest_laps/stints/race_control/weather (Phase 11)
│   │   ├── session_dashboard.py  # build_session_summary() — single source of truth for dashboard data (Phase 12)
│   │   ├── strategy_dashboard.py # build_strategy_summary() — compound usage, pit windows, insights; used by endpoint + AI context (Phase 13)
│   │   └── analytics_service.py  # build_session_analytics(), compare_drivers() — pace, compound, teammate comparisons; used by endpoint + AI context (Phase 14)
│   └── main.py
├── frontend/                     # React + Vite + TypeScript frontend (Phase 3)
├── scripts/
│   ├── create_tables.py          # creates all tables (idempotent; skips tables that already exist)
│   ├── sync_f1_data.py           # fetches and stores real F1 data; runs notification generators after sync (Phase 9.5)
│   ├── sync_openf1_session.py    # CLI: --list YEAR or --session-key KEY to sync historical data (Phase 11)
│   ├── send_due_reminder_emails.py                  # CLI script to send due reminder emails (Phase 7)
│   ├── generate_favorite_driver_alerts.py           # CLI: --list synced sessions, --session-id ID to generate alerts (Phase 15)
│   └── post_race_weekend_sync.py                     # CLI/cron: idempotent post-race-weekend sync — standings + completed session results (Phase 17)
├── .env                          # local environment variables (not committed)
├── .env.example                  # template showing required variables
└── requirements.txt
```

---

## Automated Post-Race-Weekend Sync

`scripts/post_race_weekend_sync.py` keeps GridPulse current after each F1 race
weekend. It is designed to be run on a schedule (a weekly Render Cron Job) but
is equally safe to run by hand.

### What it does

It **reuses the existing sync services** rather than duplicating them, in two
phases:

1. **Standings, calendar & schedule refresh** — calls
   `app.services.data_ingestion.sync_all()`, which upserts teams, drivers, the
   race calendar, the per-race session schedule, and **driver standings**
   (leaderboards) from Jolpica.
2. **Completed session results** — detects race weekends whose race day has
   already passed (read from the `races` table), and for each one ingests
   detailed results (laps, stints, weather, race control messages) for the
   sessions that have **finished**, via `app.services.openf1_ingestion`
   (`link_session` + the `ingest_*` functions).

Because Dashboard, Strategy, Analytics, Calendar, and Leaderboards all read
straight from the database, refreshing these tables is all that's needed — they
serve the latest data on the next request with no extra step.

> **Constructor/team standings:** the schema has a `DriverStanding` table but no
> separate constructor-standings table, so there is no constructor *leaderboard*
> to populate. The sync still refreshes team/constructor records (names) from
> Jolpica's constructor-standings endpoint via `sync_all()`. No new model is
> invented.

### Run it locally

```bash
python scripts/post_race_weekend_sync.py            # sync the current F1_SEASON
python scripts/post_race_weekend_sync.py --season 2026
python scripts/post_race_weekend_sync.py --with-alerts   # also generate favourite-driver alerts (may send emails)
```

It uses the same `DATABASE_URL` (and optional `F1_SEASON`) from your environment
/ `.env` as the rest of the app — no database URL is hardcoded, so it behaves
identically locally and on Render.

### Why it's safe to run repeatedly (idempotent)

- `sync_all()` upserts — it updates existing rows or inserts new ones, never
  creating duplicate teams, drivers, races, sessions, or standings.
- A session's detail data is treated as "already synced" once its
  `sessions.openf1_session_key` column is set; such sessions are skipped, so a
  re-run does no redundant OpenF1 fetching. **No new database columns or
  migration are required** — sync status is derived from existing data.
- Only sessions whose `date_end` is in the past are ingested, so an in-progress
  session is never half-synced. This also means a weekly cron that fires on a
  weekend **without** a race simply finds nothing to do. Completion is read from
  real session end timestamps, which correctly handles weekends finishing in
  different time zones.
- Nothing is deleted. **User-created reminders, favourites, notification
  preferences, and accounts are never touched.**

### Schedule it as a Render Cron Job

Render Cron Jobs run a one-off command on a schedule in the same environment as
your backend. Create one (Render Dashboard → **New** → **Cron Job**) pointing at
this repo:

| Setting | Value |
|---|---|
| **Command** | `python scripts/post_race_weekend_sync.py` |
| **Schedule** | `0 6 * * 1` (every Monday 06:00 UTC — after the weekend's races) |
| **Environment** | Same as the backend, must include `DATABASE_URL` (and `F1_SEASON` if not `2026`) |

The weekday is not load-bearing: the script gates on database dates, so a
Monday with no completed-but-unsynced weekend is a harmless no-op. See
[`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md#post-race-weekend-sync-cron-job) for
the full Render walkthrough.

### Logs

The script logs to stdout with timestamps (readable in Render's log viewer):
sync start, each race weekend checked, which sessions were synced (with row
counts), whether anything was skipped, when there's nothing to do, and a final
summary line. Failures log a clear error and exit non-zero so Render marks the
run as failed.

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

## Docker Local Development

Docker Compose starts the full stack — PostgreSQL, the FastAPI backend, and the React frontend — in three containers with a single command. No local PostgreSQL installation, no virtual environment activation, no separate terminal tabs.

### Prerequisites

Install **Docker Desktop** from [docker.com](https://www.docker.com/products/docker-desktop/). Once installed, open it and wait for the whale icon in your menu bar to stop animating before running any `docker` commands.

Verify Docker is running:

```bash
docker info
```

If this prints system information, Docker is up. If it says "cannot connect", Docker Desktop is not running yet.

### Environment variables

Docker Compose reads secrets from your local `.env` file. It automatically overrides two variables so the containers work correctly together:

- `DATABASE_URL` is set to `postgresql://gridpulse:gridpulse@db:5432/gridpulse` — inside Docker, `db` is the hostname of the postgres container (not `localhost`)
- `FRONTEND_URL` is set to `http://localhost:3000` — where the frontend container is served

Everything else (`JWT_SECRET_KEY`, `AI_API_KEY`, `RESEND_API_KEY`, `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, etc.) is read from your `.env` file as-is. Make sure your `.env` has real values for these before starting.

Copy the example file if you haven't already:

```bash
cp .env.example .env
```

Then fill in your credentials. The `DATABASE_URL` line in `.env` does not need to change — the compose file overrides it automatically.

### Start the full stack

```bash
docker compose up --build
```

`--build` builds all three Docker images before starting. This takes a few minutes the first time (downloading base images, installing Python packages, running `npm ci` and `npm run build`). Subsequent starts are faster because Docker caches layers.

You should see logs from all three services. When the backend is ready, you will see:

```
backend-1  | INFO:     Application startup complete.
```

**Verify each service:**

```bash
curl http://localhost:8000/health
# → {"status":"ok"}
```

Open `http://localhost:3000` in your browser — the frontend should load.

### Set up the database (first time only)

After the stack is running, open a second terminal and run the setup scripts inside the backend container:

```bash
# Create all tables
docker compose exec backend python scripts/create_tables.py

# Seed real F1 data from Jolpica
docker compose exec backend python scripts/sync_f1_data.py

# Seed the session schedule
docker compose exec backend python scripts/seed_sessions.py
```

`docker compose exec backend <command>` runs a command inside the already-running backend container. You do not need to activate a virtual environment — the container's Python already has all packages installed.

### Run migration scripts inside Docker

If you are setting up from an existing database export or adding new columns, run migration scripts the same way:

```bash
docker compose exec backend python scripts/migrate_add_openf1_session_fields.py
docker compose exec backend python scripts/migrate_create_openf1_tables.py
docker compose exec backend python scripts/migrate_add_notification_session_id.py
# ... any other migrate_*.py scripts in order
```

### Sync OpenF1 historical session data inside Docker

```bash
# List available sessions
docker compose exec backend python scripts/sync_openf1_session.py --list 2024

# Sync a specific session
docker compose exec backend python scripts/sync_openf1_session.py --session-key 9158

# Generate favourite-driver alerts for a synced session
docker compose exec backend python scripts/generate_favorite_driver_alerts.py --session-id 5
```

### Connect to the PostgreSQL container directly

The `db` container exposes port 5432 on your Mac, so you can connect with psql or a GUI tool like TablePlus:

```bash
psql postgresql://gridpulse:gridpulse@localhost:5432/gridpulse
```

### How the database volume works

PostgreSQL data is stored in a Docker named volume called `postgres_data`. This volume lives on your Mac's disk (managed by Docker) and is independent of the containers. Stopping or restarting containers does not delete your data.

```bash
# Stop containers — data is preserved
docker compose down

# Start again — all data is intact
docker compose up
```

The only way to wipe the database is to explicitly remove the volume:

```bash
# Destroys ALL database data — you will need to re-run setup scripts
docker compose down -v
```

### Stop containers

```bash
# Stop and remove containers — volume is preserved
docker compose down

# Stop without removing containers (faster restart)
docker compose stop
```

### Rebuild after code changes

If you change backend Python code or frontend TypeScript, rebuild before starting:

```bash
docker compose up --build
```

If only backend code changed, you can rebuild just that service:

```bash
docker compose up --build backend
```

### Start without rebuilding (after a stop)

```bash
docker compose up
```

No `--build` needed if no code or dependency files have changed.

### Common Docker errors and fixes

**`docker: Cannot connect to the Docker daemon`**
Docker Desktop is not running. Open Docker Desktop and wait for the whale icon to stop animating, then try again.

**`Unable to find image '...' locally` then pull error**
You ran `docker run` before `docker build`. Run `docker compose up --build` instead of `docker run` directly.

**Backend starts but `/drivers` returns 500**
The backend can reach uvicorn but cannot connect to PostgreSQL. Most common causes:
- The `db` container health check has not passed yet — wait 10–15 seconds and try again
- You forgot to create the tables: `docker compose exec backend python scripts/create_tables.py`
- You forgot to seed data: `docker compose exec backend python scripts/sync_f1_data.py`

**Frontend loads but API calls fail / CORS error**
The `VITE_API_URL` build argument was baked into the frontend image at build time. Check that it is `http://localhost:8000`. If you changed the backend port, rebuild the frontend image with `docker compose up --build frontend`.

**Port already in use (`bind: address already in use`)**
Something on your Mac is already using port 8000, 3000, or 5432. Find and stop the conflicting process, or stop your local uvicorn/Vite/PostgreSQL before starting compose.

**`docker compose exec` returns `no such service`**
Containers are not running. Run `docker compose up --build` first, then use `exec` in a second terminal.

**Changes to `.env` are not picked up**
Stop and restart the stack: `docker compose down && docker compose up`. Environment variables are injected at container start — a running container does not re-read `.env` automatically.

**Database data is gone after restart**
You ran `docker compose down -v`. The `-v` flag deletes volumes. Without `-v`, data persists. Re-run the setup scripts to restore it.

---

## Backend Testing

GridPulse has an automated test suite using pytest. Tests run against an in-memory SQLite database — the real PostgreSQL database is never touched.

### Run the tests

```bash
# From the repo root with your virtual environment active
python -m pytest
```

Expected output:

```
..................                 [100%]
18 passed in X.XXs
```

### What the tests cover

| Test file | What it tests |
|---|---|
| `tests/test_health.py` | `GET /` and `GET /health` return correct responses |
| `tests/test_auth.py` | Signup, login, duplicate email rejection, JWT token, `GET /users/me` |
| `tests/test_drivers.py` | `GET /drivers` returns a list, `GET /drivers/{id}` returns 404 when not found |

### How test isolation works

- Tests use an in-memory SQLite database via `StaticPool` — every connection shares the same database, nothing is written to disk.
- `DATABASE_URL` is forced to `sqlite:///:memory:` before any app module is imported, so the PostgreSQL connection is never attempted.
- JWT secret and algorithm are set to safe dummy values in `tests/conftest.py`.
- There are no calls to Groq, Resend, Google OAuth, or any external API in the test suite.

### Optional: run against a real Postgres database

If you want tests to run against a real database instead of SQLite (for example, to catch Postgres-specific behaviour), create a dedicated test database and set `TEST_DATABASE_URL`:

```bash
TEST_DATABASE_URL=postgresql://your_username:your_password@localhost:5432/gridpulse_test python -m pytest
```

The development database is never used by tests either way.

---

## Frontend Quality Checks

### Build

TypeScript type-check and Vite bundle:

```bash
cd frontend
npm run build
```

A successful build prints `✓ built in X.XXs` and writes output to `frontend/dist/`. The chunk size warning about the JS bundle being over 500 KB is expected for an app this size — it is not an error.

### Lint

ESLint with TypeScript support and React Hooks rules:

```bash
cd frontend
npm run lint
```

Zero errors means the lint check passes. One pre-existing warning in `GoogleCallback.tsx` about `useEffect` dependencies is expected and does not fail the check.

---

## GitHub Actions CI

Every push and pull request automatically runs two jobs in parallel on GitHub's servers.

**Backend job** — sets up Python 3.14, installs `requirements.txt`, runs `pytest`. No real database or API keys are needed — tests use SQLite in-memory with a dummy JWT secret.

**Frontend job** — sets up Node 20, runs `npm ci`, then `npm run build` and `npm run lint`.

The workflow is defined in `.github/workflows/ci.yml`. You can see results under the **Actions** tab on the GitHub repository page.

---

## Environment Variables

All environment variables are documented in [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md).

Quick summary:

| Variable | Required locally | Required in production |
|---|---|---|
| `DATABASE_URL` | Yes | Yes |
| `JWT_SECRET_KEY` | Yes | Yes |
| `FRONTEND_URL` | Yes | Yes |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI` | Only for Google sign-in | Yes |
| `RESEND_API_KEY` / `EMAIL_FROM` | Only for email | Yes |
| `AI_PROVIDER` / `AI_API_KEY` / `AI_MODEL` | Only for AI chat | Yes |
| `F1_SEASON` | No (defaults to 2026) | No |
| `VITE_API_URL` | No (defaults to localhost:8000) | Yes (frontend host) |

Copy `.env.example` to `.env` and fill in your values. The `.env` file is gitignored and must never be committed.

---

## Deployment Preparation

GridPulse is not deployed to production yet. A full deployment guide is in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md).

Recommended hosting stack:

| Piece | Service |
|---|---|
| Backend (FastAPI) | Render, Railway, or Fly.io |
| Frontend (React) | Vercel or Netlify |
| Database (PostgreSQL) | Render Postgres, Railway Postgres, or Supabase |

Key things to do before going live:
- Set all environment variables in your hosting dashboard (see `docs/ENVIRONMENT.md`)
- Add your production backend URL as an Authorized Redirect URI in Google Cloud Console
- Verify your sending domain on Resend
- Set `VITE_API_URL` to your production backend URL on the frontend host before building

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
| GET | `/sessions/{session_id}` | Single session with race name, circuit, country, and OpenF1 link status |
| GET | `/sessions/{session_id}/laps` | All stored laps for a session, ordered by driver number then lap number |
| GET | `/sessions/{session_id}/stints` | All stored stints for a session, ordered by driver number then lap start |
| GET | `/sessions/{session_id}/race-control` | All stored race control messages for a session, ordered by timestamp |
| GET | `/sessions/{session_id}/weather` | All stored weather samples for a session, ordered by timestamp |
| GET | `/sessions/{session_id}/dashboard` | Structured dashboard summary — lap stats, derived finishing order, tyre strategy, race control, weather; optional Bearer token for favourite-driver highlighting |
| GET | `/sessions/{session_id}/strategy` | Strategy dashboard — compound usage, per-driver stint sequences, pit windows, strategy-relevant RC events, weather context, rule-based insights; optional Bearer token for favourite-driver highlighting |
| GET | `/sessions/synced` | All sessions linked to an OpenF1 session key, ordered by start time descending |
| GET | `/analytics/sessions/{session_id}` | Full analytics summary — session fastest and average pace, per-driver fastest and average lap, compound averages, teammate comparisons, race context, weather; optional Bearer token for `is_favourite` highlighting |
| GET | `/analytics/sessions/{session_id}/compare` | Side-by-side driver comparison; `?driver1=4&driver2=1` query params; `404` with valid car numbers if a driver is not found |
| GET | `/analytics/sessions/{session_id}/tires` | Tire analytics only — compound pace averages and per-stint pace |

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
| POST | `/notifications/generate-favorite-driver-updates` | Yes — Bearer token | Development endpoint — manually trigger favourite-driver notification generation; returns a summary of created and skipped counts |
| POST | `/notifications/generate-favorite-driver-alerts/{session_id}` | Yes — Bearer token | Development endpoint — generate session-level favourite-driver alerts (fastest lap, strategy, RC mention, lap comparison) for a synced session; returns a per-type breakdown; `404` if session not found or not synced |

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

### AI Race Assistant endpoints

All AI endpoints require a valid JWT Bearer token. The daily limit is 20 requests per user.

| Method | Endpoint | Auth required | Description |
|---|---|---|---|
| POST | `/ai/explain` | Yes — Bearer token | Send a prompt; returns the AI's response grounded in GridPulse context; `429` if daily limit reached |
| GET | `/ai/history` | Yes — Bearer token | Return the current user's last 20 AI requests, newest first |
| GET | `/ai/usage` | Yes — Bearer token | Return `requests_today`, `daily_limit`, and `remaining` for today |

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

## Testing Automated Notification Scheduling

### Test notifications running after data sync

```bash
# Clear existing driver notifications so you can see creation happen
psql postgresql://your_username@localhost:5432/gridpulse_db \
  -c "DELETE FROM notifications WHERE type IN ('favorite_driver_standing', 'favorite_driver_wins');"

# Run the sync — notifications now run automatically at the end
python scripts/sync_f1_data.py
```

Expected output (after the existing sync summary):

```
Data sync completed.

Favourite-driver notification generation started.

=== Favourite Driver Notifications ===

[Standing Notifications]
  Created                   : 1
  Skipped (duplicate)       : 0
  Skipped (no standing data): 0
  Skipped (opted out)       : 0
  Emails sent               : 1
  Emails failed             : 0

[Wins Notifications]
  Created                   : 0
  Skipped (duplicate)       : 0
  Skipped (no wins yet)     : 1
  Skipped (no standing data): 0
  Skipped (opted out)       : 0
```

Run the sync again immediately — both generators should show `Created: 0` and the appropriate skip counts, confirming dedup works through the automated flow.

### Test the dev trigger endpoint

1. Start the backend: `uvicorn app.main:app --reload`
2. Open `http://127.0.0.1:8000/docs`
3. Log in via **POST /auth/login** and copy the `access_token`
4. Click the **Authorize** padlock, paste the token, click **Authorize**
5. Find **POST /notifications/generate-favorite-driver-updates** → **Try it out** → **Execute**
6. First call (with existing notifications): response should show `notifications_created: 0` and `duplicates_skipped` matching your existing notification count
7. Delete notifications from the `/notifications` page in the frontend, then call the endpoint again — `notifications_created` should be `1` or `2`
8. Call it a second time — `notifications_created: 0`, `duplicates_skipped` reflects the newly created count

### To set up a cron job (optional)

To run the sync automatically on a schedule — for example, every Sunday at 06:00:

```bash
crontab -e
```

Add:
```
0 6 * * 0 cd /path/to/gridpulse && source venv/bin/activate && python scripts/sync_f1_data.py >> logs/sync.log 2>&1
```

No code changes are needed. The sync script already handles data refresh and notification generation in one command.

---

## Testing the AI Race Assistant

### Get a Groq API key

1. Go to [console.groq.com](https://console.groq.com) and sign up (free)
2. Click **API Keys** → **Create API Key**
3. Copy the key (it starts with `gsk_`)
4. Add to your `.env`:
   ```
   AI_PROVIDER=groq
   AI_API_KEY=gsk_your_key_here
   AI_MODEL=llama-3.1-8b-instant
   ```
5. Restart the backend: `uvicorn app.main:app --reload`

### Run the migration (existing databases only)

If you already have a database from a previous phase, create the `ai_requests` table:

```bash
python scripts/migrate_create_ai_requests_table.py
```

Expected output:
```
Running migration: create ai_requests table...
Done. ai_requests table created (or already existed — safe to run again).
```

Fresh databases created with `create_tables.py` include the table automatically.

### Test in FastAPI docs

1. Start the backend: `uvicorn app.main:app --reload`
2. Open `http://127.0.0.1:8000/docs`
3. Log in via **POST /auth/login** and copy the `access_token`
4. Click the **Authorize** padlock, paste the token, click **Authorize**

**Ask a question:**

5. Find **POST /ai/explain** → **Try it out** and enter:
   ```json
   {
     "prompt": "Who are my favourite drivers and where are they in the standings?",
     "request_type": "general"
   }
   ```
6. Click **Execute** — you should get a `200` response with the AI's answer in the `response` field

**Check history:**

7. Find **GET /ai/history** → **Try it out** → **Execute** — your question and response should appear

**Check usage:**

8. Find **GET /ai/usage** → **Execute** — you should see `requests_today`, `daily_limit: 20`, and `remaining`

**Test the daily limit:**

Insert 20 fake rows in psql to trigger the limit without spending real API calls:

```sql
INSERT INTO ai_requests (user_id, prompt, response, request_type, created_at)
SELECT 1, 'test', 'test', 'general', now()
FROM generate_series(1, 20);
```

Replace `1` with your actual user ID. Then call **POST /ai/explain** — you should get `429` with `"Daily limit of 20 AI requests reached. Try again tomorrow."` To clean up:

```sql
DELETE FROM ai_requests WHERE response = 'test';
```

### Test in the frontend

1. Start both servers: `uvicorn app.main:app --reload` and `cd frontend && npm run dev`
2. Log in and click **AI** in the navbar
3. Type a question in the prompt box and click **Ask** (or press ⌘+Enter)
4. Watch the "Analysing…" spinner, then the response card appears below
5. Ask another question — the previous response moves to the history section
6. Click any history item to expand the full response; click again to collapse

**Suggested prompts to try:**

| Prompt | What it tests |
|---|---|
| `Who are my favourite drivers?` | Context grounding — user's personal data |
| `What are the current standings?` | Context grounding — top-10 standings table |
| `What are my upcoming sessions?` | Context grounding — session schedule |
| `Who won the last race?` | Missing data — should say GridPulse doesn't have that |
| `What was Verstappen's fastest lap in Bahrain?` | Missing data — should refuse to invent a time |
| `How does DRS work?` | General F1 knowledge — should explain and flag it as general knowledge |
| `Who is on pole for the next race?` | Missing data — qualifying not in GridPulse |
| `Who probably won the most races based on their points?` | Grounding guard — should not infer results from standings |

**Test grounding edge cases:**

- Ask for a race result — the AI should say "GridPulse doesn't have that data yet" not invent one
- Ask "what's happening live right now?" — the AI should note it has no live feed and reference the snapshot timestamp
- Ask about a concept like "what is undercut strategy?" — the AI should answer and label it as general F1 knowledge

---

## OpenF1 Session Sync

### Run the migrations (existing databases only)

If your database was created before Phase 11, run both migration scripts first:

```bash
python scripts/migrate_add_openf1_session_fields.py
python scripts/migrate_create_openf1_tables.py
```

Both scripts use `IF NOT EXISTS` and are safe to run more than once. Fresh databases created with `create_tables.py` include all Phase 11 tables automatically.

### List available sessions

To find the `session_key` for a session you want to sync:

```bash
python scripts/sync_openf1_session.py --list 2024
```

Expected output:

```
session_key    session_name           circuit                        date_start
--------------------------------------------------------------------------------------
9149           Practice 1             Bahrain                        2024-02-29T11:30:00+00:00
9150           Practice 2             Bahrain                        2024-02-29T15:00:00+00:00
9151           Qualifying             Bahrain                        2024-03-01T15:00:00+00:00
9158           Race                   Bahrain                        2024-03-02T15:00:00+00:00
...
```

### Sync a session

```bash
python scripts/sync_openf1_session.py --session-key 9158
```

Expected output:

```
=== Syncing session_key=9158 ===

Step 1/5 — Linking session...
  Linked session_key=9158 → sessions.id=5 (Bahrain Grand Prix — Race)
  session_id=5

Step 2/5 — Ingesting weather samples...
  inserted=112  skipped=0

Step 3/5 — Ingesting race control messages...
  inserted=34  deleted(replaced)=0

Step 4/5 — Ingesting stints...
  inserted=40  skipped=0

Step 5/5 — Ingesting laps...
  inserted=1140  skipped=0

=== Sync complete ===
  Weather samples : 112 inserted
  Race control    : 34 inserted (0 replaced)
  Stints          : 40 inserted
  Laps            : 1140 inserted
```

Running the sync again for the same session is safe — existing rows are skipped (laps, stints, weather) or replaced (race control messages).

### Verify synced data in PostgreSQL

After syncing a session, connect to psql and check the tables:

```bash
psql postgresql://your_username@localhost:5432/gridpulse_db
```

```sql
-- Check the session was linked
SELECT id, session_name, openf1_session_key, circuit_short_name, country_name
FROM sessions
WHERE openf1_session_key IS NOT NULL;

-- Count laps per driver
SELECT driver_number, COUNT(*) AS laps
FROM laps
WHERE session_id = 5
GROUP BY driver_number
ORDER BY driver_number;

-- Fastest lap per driver (excluding pit-out laps)
SELECT driver_number, MIN(lap_duration) AS fastest_lap
FROM laps
WHERE session_id = 5
  AND is_pit_out_lap = false
  AND lap_duration IS NOT NULL
GROUP BY driver_number
ORDER BY fastest_lap;

-- Tyre compounds used
SELECT compound, COUNT(*) AS stints
FROM stints
WHERE session_id = 5
  AND compound IS NOT NULL
GROUP BY compound
ORDER BY stints DESC;

-- Race control messages
SELECT date, lap_number, flag, message
FROM race_control_messages
WHERE session_id = 5
ORDER BY date;

-- Weather range
SELECT
  MIN(air_temperature) AS air_min,
  MAX(air_temperature) AS air_max,
  MIN(track_temperature) AS track_min,
  MAX(track_temperature) AS track_max,
  BOOL_OR(rainfall) AS had_rain,
  COUNT(*) AS readings
FROM weather_samples
WHERE session_id = 5;
```

### Test the historical data endpoints

Start the backend and test each endpoint:

```bash
uvicorn app.main:app --reload
```

```bash
# Get session detail (replace 5 with your actual session_id)
curl http://localhost:8000/sessions/5 | python3 -m json.tool

# Laps (returns per-driver per-lap rows)
curl http://localhost:8000/sessions/5/laps | python3 -m json.tool | head -60

# Stints
curl http://localhost:8000/sessions/5/stints | python3 -m json.tool

# Race control messages
curl http://localhost:8000/sessions/5/race-control | python3 -m json.tool

# Weather samples
curl http://localhost:8000/sessions/5/weather | python3 -m json.tool | head -40

# 404 for non-existent session
curl -i http://localhost:8000/sessions/99999/laps
```

### Test the session detail page

1. Start both servers: `uvicorn app.main:app --reload` and `cd frontend && npm run dev`
2. Go to `/calendar` and expand any past race
3. Past session names are now underlined links — click one to open `/sessions/:id`
4. Before syncing: all four sections show "No data synced yet" and the header shows "Not synced"
5. After syncing (run the sync script above): the page fills in with lap counts, compound badges, race control messages, and weather stats
6. The header shows a green "Data synced" badge

---

## Testing the Historical Race Dashboard

### Prerequisites

The dashboard page only shows data for sessions that have been synced via `sync_openf1_session.py`. Sync at least one race session before testing the dashboard (see the **OpenF1 Session Sync** section above for the `--list` and `--session-key` steps).

### Test the backend endpoint

```bash
uvicorn app.main:app --reload
```

```bash
# Replace 5 with the session_id of a synced session
curl http://localhost:8000/sessions/5/dashboard | python3 -m json.tool
```

Expected: a JSON object with `session_id`, `session_name`, `is_synced: true`, and populated `lap_stats`, `finishing_order`, `stint_summary`, `race_control`, and `weather` sections.

For an unsynced session, the `has_*` flags will be `false` and the data sections will be empty:
```bash
curl http://localhost:8000/sessions/1/dashboard | python3 -m json.tool
# Expect: is_synced: false, has_lap_data: false, etc.
```

### Test favourite-driver highlighting

With a logged-in user who has favourited at least one driver:

```bash
# Get a JWT token
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpass"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl http://localhost:8000/sessions/5/dashboard \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | grep is_favourite
```

Expected: `"is_favourite": true` for any driver the user has favourited.

### Test the frontend dashboard page

1. Start both servers: `uvicorn app.main:app --reload` and `cd frontend && npm run dev`
2. Go to `http://localhost:5173/calendar`
3. Expand a past race — each session row shows a **Dashboard →** link
4. Click it — you are taken to `/sessions/:id/dashboard`
5. If the session has not been synced: every section shows its specific empty-state message (e.g. "No lap data has been synced for this session yet.") and the page-level footnote about OpenF1 sync dependency is visible
6. If the session has been synced: all sections fill in with real data

### Verify each dashboard section

| Section | What to check |
|---|---|
| Session summary | Race name, circuit, country, date match the session |
| Lap summary | Driver count and max lap number match psql query on `laps` table |
| Finishing order | P1 driver has the highest max_lap; lapped drivers show "+N lap(s)" |
| Tyre strategy | Compound pills match the `stints` table; used tyres show age at start |
| Race control | Key events match the `race_control_messages` table; safety car lap number is accurate |
| Weather | Air/track temps and latest reading match the `weather_samples` table |

### Test favourite-driver highlighting in the frontend

1. Log in and favourite at least one driver on the Drivers page
2. Navigate to the dashboard for a synced race session
3. The favourited driver should have a red star (★) in the finishing order and tyre strategy tables, and a subtle red row background

### Test AI questions about dashboard data

After syncing a session, go to `http://localhost:5173/ai` and try:

| Prompt | Expected behaviour |
|---|---|
| `Who won the race?` | Gives P1 from derived finishing order with an approximation caveat |
| `What tyres did [driver] use?` | Lists all stints from the context with compound and lap range |
| `Was there a safety car?` | Answers from the key race events bullet in context |
| `What was the weather like?` | Gives session range and latest reading |
| `What was [driver]'s fastest lap?` | Says GridPulse does not store individual lap times |
| `What happened in qualifying?` | Says GridPulse does not store qualifying results |

---

## Testing the Strategy Dashboard

### Prerequisites

The Strategy Dashboard only shows data for sessions that have been synced via `sync_openf1_session.py`. Sync at least one race session before testing (see the **OpenF1 Session Sync** section above).

### Test the backend endpoint

```bash
uvicorn app.main:app --reload
```

```bash
# Replace 15 with the session_id of a synced session
curl http://localhost:8000/sessions/15/strategy | python3 -m json.tool
```

Expected: a JSON object with `session_id`, `is_synced: true`, populated `compound_usage`, `driver_strategies`, `pit_windows`, `race_control`, `weather`, and `insights`.

For an unsynced session:
```bash
curl http://localhost:8000/sessions/1/strategy | python3 -m json.tool
# Expect: is_synced: false, has_stint_data: false, driver_strategies: [], insights: [...]
```

### Test favourite-driver highlighting

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpass"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl http://localhost:8000/sessions/15/strategy \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | grep is_favourite
```

Expected: `"is_favourite": true` for any driver the user has favourited.

### Test the frontend Strategy Dashboard

1. Start both servers: `uvicorn app.main:app --reload` and `cd frontend && npm run dev`
2. Go to `http://localhost:5173/calendar`
3. Expand any past race — each session row shows both **Dashboard →** and **Strategy →** links
4. Click **Strategy →** — you are taken to `/sessions/:id/strategy`
5. If the session has not been synced: all sections show "No data synced yet" empty states
6. If the session has been synced: all sections fill in with real data

### Verify each strategy section

| Section | What to check |
|---|---|
| Session summary | Race name, circuit, country, and date match the session |
| Insights | At least one insight appears; no invented data — each sentence references counts or names from the data |
| Compound usage | Cards match the `stints` table compound breakdown; avg stint length is plausible |
| Driver strategies | Each driver's compound sequence matches their stints; longest stint is highlighted in amber |
| Stop count groups | Grouped correctly — a driver with 2 stints shows "1 stop" |
| Pit windows | Lap ranges cluster around the real pit lap numbers from the `stints` table |
| Race control | Only strategy-relevant messages (safety car, VSC, red flag) appear; blue-flag messages are excluded |
| Weather | Session range and latest reading match the `weather_samples` table |

### Test favourite-driver highlighting in the frontend

1. Log in and favourite at least one driver on the Drivers page
2. Navigate to the strategy dashboard for a synced race session
3. The favourited driver's card should appear first in the driver strategies list, with a red border and a ★ star

### Test AI questions about strategy data

After syncing a session, go to `http://localhost:5173/ai` and try:

| Prompt | Expected behaviour |
|---|---|
| `What tyre compounds were used in the Japanese Grand Prix?` | Lists compounds with stint counts and averages |
| `How many pit stops did drivers make?` | Gives stop-count breakdown (e.g. "19 drivers made 1 stop") |
| `What tyres did [driver] run?` | Reads the per-driver compound sequence from context |
| `Was there a safety car and could it have affected strategy?` | Answers from strategy RC events; uses cautious language |
| `What was the track temperature and could it have affected tyres?` | Gives temperature range; notes variance if large |
| `Who ran the longest stint?` | Names the driver and compound from the insights block |
| `What was [driver]'s fastest lap time?` | Says GridPulse does not store individual lap times |
| `Did anyone undercut Verstappen?` | Declines to invent strategy interpretations |

**Note on AI accuracy:** GridPulse uses `llama-3.1-8b-instant` by default. This small model handles aggregate questions well (compound counts, stop totals) but may miss precise per-driver lookups in long contexts. For more reliable per-driver answers, try upgrading to `llama-3.3-70b-versatile` in your `.env` file.

---

## Testing the Analytics Dashboard

### Prerequisites

The Analytics Dashboard only shows data for sessions that have been synced via `sync_openf1_session.py`. Sync at least one race session before testing (see the **OpenF1 Session Sync** section above for the `--list` and `--session-key` steps).

### Test the backend endpoints

```bash
uvicorn app.main:app --reload
```

```bash
# Replace 5 with the session_id of a synced session
curl http://localhost:8000/analytics/sessions/5 | python3 -m json.tool

# Tire analytics only
curl http://localhost:8000/analytics/sessions/5/tires | python3 -m json.tool

# Driver comparison (car numbers 4 and 1)
curl "http://localhost:8000/analytics/sessions/5/compare?driver1=4&driver2=1" | python3 -m json.tool
```

Expected for a synced session: a JSON object with `session_id`, `has_lap_data: true`, `session_fastest_lap`, `session_fastest_driver`, and populated `driver_pace`, `tire_analytics`, `teammate_comparisons`, `race_context`, and `weather` fields.

For an unsynced session all `has_*` flags will be `false` and data sections will be empty:
```bash
curl http://localhost:8000/analytics/sessions/1 | python3 -m json.tool
# Expect: is_synced: false, has_lap_data: false, driver_pace: []
```

For an invalid car number in the compare endpoint:
```bash
curl "http://localhost:8000/analytics/sessions/5/compare?driver1=4&driver2=99" | python3 -m json.tool
# Expect: 404 with a "valid_car_numbers" list in the detail
```

### Test favourite-driver highlighting

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpass"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl http://localhost:8000/analytics/sessions/5 \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool | grep is_favourite
```

Expected: `"is_favourite": true` for any driver the user has favourited.

### Test the frontend Analytics Dashboard

1. Start both servers: `uvicorn app.main:app --reload` and `cd frontend && npm run dev`
2. Go to `http://localhost:5173/calendar`
3. Expand any past race — each session row shows **Dashboard →**, **Strategy →**, and **Analytics →** links
4. Click **Analytics →** — you are taken to `/sessions/:id/analytics`
5. If the session has not been synced: every section shows its specific empty-state message and a footnote about OpenF1 sync dependency is visible
6. If the session has been synced: all sections fill in with real data

### Verify each analytics section

| Section | What to check |
|---|---|
| Session pace | Session fastest lap matches `MIN(lap_duration)` from psql on the `laps` table (excluding pit-out laps) |
| Driver pace table | Per-driver fastest laps are ordered fastest first; average only appears for drivers with ≥3 timed laps |
| Compound pace | Average times match the compounds in the `stints` table; only appears when stints have `lap_start` / `lap_end` set |
| Lap count chart | Bar lengths are proportional to total lap count; favourite driver bar is red |
| Fastest lap gap chart | The session-fastest driver shows a near-zero bar; others show their gap in seconds |
| Compound usage chart | Bars appear in SOFT → MEDIUM → HARD → INTERMEDIATE → WET order |
| Teammate comparisons | Deltas are negative when driver A is faster; teams without both drivers having lap data are not shown |
| Race control context | Safety car lap numbers match `race_control_messages` table rows with SAFETY CAR in the message |
| Weather | Latest reading matches the most recent row in `weather_samples` for the session |

### Test the driver comparison tool

1. Open the Analytics page for a synced session
2. Both car number dropdowns should be populated with drivers who have lap data
3. Select two different drivers and click **Compare**
4. A side-by-side card appears: fastest lap, average lap, delta (negative = left driver faster)
5. Per-driver stint tables appear below the summary row
6. Select the same driver in both dropdowns — the backend still returns a valid response (delta = 0)
7. Before selecting any drivers, the Compare button is disabled

### Test AI questions about analytics data

After syncing a session, go to `http://localhost:5173/ai` and try:

| Prompt | Expected behaviour |
|---|---|
| `Who was the fastest driver in the Bahrain race?` | Names the driver and gives the fastest lap time in seconds with an approximation note |
| `What was Leclerc's average pace?` | Reads the per-driver average from context; qualifies as derived from stored laps |
| `Which tyre compound was fastest?` | Gives compound averages from context if compound pace is available |
| `Were there any safety cars?` | Lists the safety car laps from the analytics block |
| `What was [driver]'s fastest lap?` | Gives the time if in context; says "GridPulse does not have enough synced lap data" if `no_lap_data` |
| `What were all of Verstappen's lap times?` | Says full per-lap time sequences are not available — only fastest and average |

---

## Testing Favourite Driver Session Alerts

### Prerequisites

Session alerts require:
1. At least one user account with a favourited driver
2. A session synced from OpenF1 (`sync_openf1_session.py --session-key <key>`)
3. The `related_session_id` migration applied (existing databases only)

**Apply the migration (existing databases only):**

```bash
python scripts/migrate_add_notification_session_id.py
```

Fresh databases created with `create_tables.py` include the column automatically.

### Generate alerts via the CLI script

```bash
# Step 1: find the GridPulse session_id of a synced session
python scripts/generate_favorite_driver_alerts.py --list
```

Expected output:

```
ID     Session            Race                                     OpenF1 key
--------------------------------------------------------------------------------
5      Race               Bahrain Grand Prix                       9158

Found 1 synced session(s).
Use --session-id <ID> from the first column to generate alerts.
```

```bash
# Step 2: generate alerts for that session
python scripts/generate_favorite_driver_alerts.py --session-id 5
```

Expected output (first run, with a favourite driver in the session):

```
=== Favourite-driver session alerts — session_id=5 ===

  Session       : Bahrain Grand Prix — Race (id=5)
  Drivers with data checked : 1

  [Fastest lap in session]
    Created          : 1
    Skipped (dup)    : 0
    Emails sent      : 1

  [Strategy summary]
    Created          : 1
    Skipped (dup)    : 0
    Emails sent      : 1

  [Race control mention]
    Created          : 0
    Skipped (dup)    : 0
    Emails sent      : 0

  [Lap data note]
    Created          : 0
    Skipped (dup)    : 0
    Emails sent      : 0

  Total created  : 2
  Total skipped  : 0
  Emails sent    : 2
```

Running the script again immediately:

```
  Total created  : 0
  Total skipped  : 2
  Tip: all alerts already exist for this session.
  To regenerate, delete the existing notifications from psql:
    DELETE FROM notifications
    WHERE related_session_id = 5
      AND type LIKE 'favorite_driver_%';
```

### Generate alerts via the API endpoint

```bash
uvicorn app.main:app --reload
```

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"you@example.com","password":"yourpass"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")

curl -s -X POST http://localhost:8000/notifications/generate-favorite-driver-alerts/5 \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

Expected response (first run):

```json
{
  "session_id": 5,
  "session_name": "Race",
  "race_name": "Bahrain Grand Prix",
  "is_synced": true,
  "favorite_drivers_checked": 1,
  "alerts": {
    "favorite_driver_fastest_lap": {"created": 1, "skipped": 0, "emails_sent": 1, "emails_failed": 0},
    "favorite_driver_strategy":    {"created": 1, "skipped": 0, "emails_sent": 1, "emails_failed": 0},
    "favorite_driver_rc_mention":  {"created": 0, "skipped": 0, "emails_sent": 0, "emails_failed": 0},
    "favorite_driver_lap_comparison": {"created": 0, "skipped": 0, "emails_sent": 0, "emails_failed": 0}
  },
  "total_created": 2,
  "total_skipped": 0,
  "emails_sent": 2,
  "emails_failed": 0
}
```

### Test the Notifications page

1. Start both servers: `uvicorn app.main:app --reload` and `cd frontend && npm run dev`
2. Log in and go to `http://localhost:5173/notifications`
3. Session alerts should appear with their type-specific icons and badges:
   - Fastest lap → purple bolt icon + **Fastest lap** badge
   - Strategy → orange tire icon + **Strategy** badge
   - RC mention → yellow flag icon + **Race control** badge
   - Lap comparison → slate triangle icon + **Lap note** badge
4. Mark an alert as read — the icon dims and the row fades to 50% opacity
5. Delete an alert — the row disappears and the unread count badge updates

### Test the Dashboard alert summary

1. Log in and go to `http://localhost:5173/dashboard`
2. The **Driver Updates** section should now show session alert notifications alongside standing/wins notifications
3. Each card should display the type-appropriate icon and a small type badge
4. The section shows up to 4 items; click **All notifications →** to see the full list

### Test session alert panels on session pages

1. Navigate to `/sessions/:id/dashboard` for a synced session
2. If the logged-in user has favourite-driver alerts for that session, a compact **"Your Driver Alerts"** panel appears above the Lap Summary
3. Navigate to `/sessions/:id/strategy` for the same session
4. If a strategy alert exists, a compact **"Your Strategy Alerts"** panel appears above the Strategy Insights section with an orange tire icon
5. Both panels link to `/notifications` — click to view the full alert with the Mark read and Delete options
6. Log out and reload the same pages — the alert panels are hidden (alerts are user-specific)

### Test AI questions about session alerts

After generating alerts, go to `http://localhost:5173/ai` and try:

| Prompt | Expected behaviour |
|---|---|
| `What alerts do I have?` | Lists entries from the Favourite-Driver Alerts section in context |
| `Did my favourite driver set the fastest lap?` | Confirms or denies based on the fastest lap alert; gives the stored lap time |
| `What tyres did my favourite driver run?` | Reads the strategy alert message (compound sequence and stop count) |
| `Was my favourite driver mentioned in race control?` | Confirms from the RC mention alert if it exists; says data is not available if not |
| `Did my favourite driver retire from the race?` | Quotes the lap comparison alert (laps completed vs max); adds the no-official-classification disclaimer |
| `How many positions did my favourite driver gain?` | States that GridPulse has no per-lap position column; offers the derived finishing order if available |
| `What was my favourite driver's pit stop time?` | Says official pit stop durations are not stored in GridPulse |

---

## FastF1 — Future Integration Plan

FastF1 is a Python library (not used in Phase 11) that provides data OpenF1 does not:

| Capability | OpenF1 | FastF1 |
|---|---|---|
| Lap times, stints, race control, weather | Yes | Yes |
| Car telemetry (speed, throttle, brake, RPM, gear, DRS) | No | Yes |
| GPS position data (X/Y on track) | No | Yes |
| Driver vs driver lap telemetry overlays | No | Yes |
| Track map geometry | No | Yes |
| Historical seasons before 2023 | Limited | Yes |
| Pre-built Pandas DataFrames | No | Yes |

**When to use FastF1 instead of OpenF1:**
Use OpenF1 for anything quickly fetchable via REST — laps, stints, race control, weather. Use FastF1 for anything that requires "what happened on track": speed traces, braking points, car position, lap delta comparisons between drivers.

**Caching concerns:**
FastF1 downloads session data from F1's servers and caches it locally as `.ff1pkl` files. A full race weekend's telemetry cache is 300–600 MB. The first load of a session can take 30–90 seconds. FastF1 must never run in a request/response cycle — only in background jobs or pre-ingestion scripts. A `fastf1.Cache.enable_cache('/path/to/cache')` call is required before any session load, and the cache path must be on persistent storage.

**Why FastF1 is delayed:**
FastF1 data (telemetry, track maps, driver comparisons) is meaningless without a chart or visualisation layer to display it. The right sequence is to build the display layer first, then pull in the data source that feeds it. FastF1 also adds heavy dependencies (`pandas`, `numpy`, `matplotlib`) and a cache architecture decision that belongs in the analytics phase, not in the current lightweight ingestion layer.

---

## What Is Not Included Yet

The following features are planned but not yet built:

**AI Race Assistant (partial — Phase 10 complete, gaps remaining):**
- Suggested prompt cards on the AI page — planned for a future UI pass
- Multi-turn conversation threading — each question is currently independent (single-turn Q&A)
- Streaming responses (WebSocket or Server-Sent Events)

**Historical data (partial — Phase 14 complete, gaps remaining):**
- Official race classifications — the dashboard finishing order is derived from lap timing; post-race penalties and DSQs are not reflected
- Qualifying results and grid positions — no `qualifying_results` table yet
- Automatic session sync — the sync script must still be run manually
- FastF1 telemetry (speed traces, throttle, GPS position) — planned for analytics phase
- Pit stop duration data — pit windows are derived from stint transitions, not official timing
- Tyre degradation trend analysis and full per-lap time sequences per driver — only fastest and average lap times are currently computed
- Qualifying vs race pace comparison — requires syncing and linking a qualifying session to the same race

**Notifications and alerts:**
- Automatic alert generation after OpenF1 sync — alerts must still be generated manually via `scripts/generate_favorite_driver_alerts.py` or the dev endpoint
- Position change alerts (gained/lost positions during a race) — the `laps` table has no per-lap position column
- Official retirement or DNF notifications — requires a `race_results` table; only lap count comparison is currently available
- Per-qualifying position notifications — requires a `qualifying_results` table
- Push notifications
- The following alert types are explicitly not supported because the required data does not exist: penalty confirmation via text search, official race classifications, grid positions

**Data and sync:**
- Scheduled or automatic data sync — notification generation runs inside the sync script, but the sync itself must still be triggered manually or via a cron job
- Scheduled or automatic reminder delivery — the delivery logic exists but no background job or cron runs it yet; use `scripts/send_due_reminder_emails.py` or `POST /email/send-due-reminders` manually for now
- Session times are seeded from approximate UTC values, not pulled live from Jolpica — real session times will be added in a future sync update
- Constructor standings endpoint
- Team base location data

**Infrastructure:**
- Live race data of any kind
- WebSockets
- Redis
- Alembic database migrations
- Production deployment — CI runs on GitHub Actions but the app is not deployed to a public host yet (see [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) for the preparation guide)
- ML predictions

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
In-app and optional email notifications for favourited drivers. Two notification types are currently supported: a championship standings snapshot and a race wins update, both generated from existing `DriverStanding` data. Per-race and per-qualifying result notifications are planned once result tables are added.

**Phase 9.5 — Automated Notification Scheduling** *(complete)*
Favourite-driver notification generation now runs automatically at the end of the F1 data sync script. A protected development endpoint (`POST /notifications/generate-favorite-driver-updates`) allows manual triggering without re-running the full sync.

**Phase 10 — AI Race Assistant** *(complete)*
Protected `/ai` page for signed-in users. Ask questions about standings, favourite drivers, sessions, and reminders grounded in GridPulse database context. Groq (free tier) is the default provider; Anthropic is supported as an alternative. Responses are stored in `ai_requests` with a 20-request daily limit. The AI is explicitly grounded — it cannot invent race results, qualifying times, or live data.

**Phase 11 — OpenF1 / FastF1 Historical Data Upgrade** *(complete)*
OpenF1 API client, ingestion service, and sync script. Four new tables: laps, stints, race control messages, weather samples. Five new REST endpoints. Session detail frontend page at `/sessions/:id`. AI context updated to include historical session summaries.

**Phase 12 — Historical Race Dashboard** *(complete)*
Structured per-session dashboard at `GET /sessions/{id}/dashboard` and `/sessions/:id/dashboard`. Sections: derived finishing order, tyre strategy per driver, key race control events, weather with latest reading, favourite-driver highlighting. AI context refactored to use the dashboard service as a single source of truth; missing-data flags, per-driver lap table, and token budget safeguards added.

**Phase 13 — Strategy Dashboard** *(complete)*
Dedicated strategy page at `GET /sessions/{id}/strategy` and `/sessions/:id/strategy`. Sections: compound usage cards, per-driver stint sequences with longest-stint highlighting, stop-count grouping, derived pit windows, strategy-relevant race control events with context notes, weather conditions. Rule-based insights derived from stored data — no ML. Favourite-driver cards sorted first. Navigation links added to Calendar and Session Dashboard. AI context updated with compact strategy summaries; system prompt updated with explicit strategy-grounding rules; token budget safeguards maintained.

**Phase 14 — Advanced Analytics** *(complete)*
Analytics page at `GET /analytics/sessions/{id}` and `/sessions/:id/analytics`. Sections: session pace summary, per-driver fastest and average lap table, compound pace averages, teammate comparison deltas, safety car and red flag context, weather, and three Recharts bar charts (lap count, fastest lap gap, compound usage). Side-by-side driver comparison tool. Navigation links added to Calendar, Session Dashboard, and Strategy Dashboard. AI context updated with per-driver pace, compound averages, and SC/RF laps; analytics-aware system prompt with explicit missing-data rules; `_AI_MAX_ANALYTICS_DRIVERS = 20` token cap.

**Phase 15 — Sync-Based Favourite Driver Session Alerts** *(complete)*
Per-session alert detection from stored OpenF1 data — not live timing. Four alert types supported: fastest stored lap, tyre strategy summary, race control mention (structured `driver_number` column), and lap comparison note (race/sprint sessions only). Manual CLI script and dev API endpoint for alert generation. Frontend Notifications page updated with type-specific icons and badges. Dashboard Driver Updates expanded to all six `favourite_driver_*` types. Compact alert panels added to Session Dashboard and Strategy Dashboard. AI context updated with alert section and explicit grounding rules for alert questions.

**Phase 16 — Docker, Testing, CI/CD, and Deployment** *(complete except production deploy)*
Docker and Docker Compose for local development — PostgreSQL, FastAPI backend, and React frontend start with a single `docker compose up --build`. Automated pytest suite (18 tests) using SQLite in-memory so the real database is never touched. Frontend build (`tsc -b && vite build`) and lint (ESLint + typescript-eslint + react-hooks) run as quality checks. GitHub Actions CI runs both jobs on every push and pull request with no real secrets or external API calls. Environment variables documented in [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md). Deployment preparation guide in [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md). Production deployment is not yet complete.

**Phase 17 — Automated Post-Race-Weekend Sync** *(complete)*
Idempotent `scripts/post_race_weekend_sync.py` that refreshes standings/calendar/sessions via `sync_all()` and ingests completed session results via the OpenF1 ingestion service. Race-weekend completion is detected from the `races` table plus per-session `date_end`, so it is safe to run weekly (e.g. a Render Cron Job) — weekends without a completed-but-unsynced race are a no-op. No new database columns: sync status is derived from the existing `sessions.openf1_session_key` column. No data is deleted and user-created content is never touched. See [Automated Post-Race-Weekend Sync](#automated-post-race-weekend-sync).

---

## Development Notes

- The `.env` file is gitignored and will never be committed. Never hardcode credentials in source files. See [`docs/ENVIRONMENT.md`](docs/ENVIRONMENT.md) for the full variable reference.
- `scripts/create_tables.py` is safe to re-run. It skips tables that already exist.
- `scripts/sync_f1_data.py` is safe to re-run multiple times. It uses upsert logic and will not create duplicate rows.
- `scripts/seed.py` inserts a small hardcoded dataset used during Phase 1 development. It is no longer needed now that `sync_f1_data.py` exists.
- There is no Alembic migration system yet. For model changes, drop the affected tables manually and recreate them with `create_tables.py`.
- Data sync can be run manually (`scripts/sync_f1_data.py`) or automatically after each race weekend (`scripts/post_race_weekend_sync.py`, see [Automated Post-Race-Weekend Sync](#automated-post-race-weekend-sync)).
- Run `python -m pytest` to execute the test suite. Tests use SQLite in-memory and never touch the development database.
- GitHub Actions runs `pytest` and the frontend build+lint automatically on every push. Check the **Actions** tab on GitHub to see results.
