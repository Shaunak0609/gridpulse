# GridPulse Environment Variables

This document describes every environment variable the app reads, whether it is
required, its default value, and where to get it.

The backend reads variables from `.env` at startup via `python-dotenv`.
The frontend reads variables at build time via Vite — they are baked into the
JavaScript bundle and cannot be changed at runtime.

Copy `.env.example` to `.env` and fill in your values before starting the server:

```
cp .env.example .env
```

`.env` is in `.gitignore` and must never be committed.

---

## Database

### `DATABASE_URL`
**Required.** PostgreSQL connection string.

```
DATABASE_URL=postgresql://your_username:your_password@localhost:5432/gridpulse
```

- Local dev (uvicorn directly): use your local Postgres credentials.
- Docker Compose: the compose file overrides this to use the `db` service — you do
  not need to change it.
- Production: use the connection string provided by your database host (Render,
  Railway, Supabase, etc.).

### `TEST_DATABASE_URL`
**Optional.** If set, pytest uses this database instead of in-memory SQLite.

```
# TEST_DATABASE_URL=postgresql://your_username:your_password@localhost:5432/gridpulse_test
```

You do not need to set this. The default (in-memory SQLite) is safe and fast. Only
set it if you specifically want pytest to run against a real Postgres database.
The development database is never touched by tests either way.

---

## Auth / JWT

### `JWT_SECRET_KEY`
**Required.** Random string used to sign and verify login tokens.

```
JWT_SECRET_KEY=your-secret-key-here
```

Generate a secure value with:
```
python -c "import secrets; print(secrets.token_hex(32))"
```

If this is leaked, an attacker can forge login tokens for any account. Use a
different value in production than in local development. Never commit it.

### `JWT_ALGORITHM`
**Optional.** Default: `HS256`. The algorithm used to sign JWTs.

Do not change this — `HS256` is the correct value for the current setup.

### `JWT_EXPIRE_MINUTES`
**Optional.** Default: `60`. How many minutes a login token stays valid.

---

## Google OAuth

All three variables are required only if you want Google sign-in to work.
If they are missing, the `/auth/google/*` routes will fail but the rest of the
app (email/password auth, all other routes) continues to work.

### `GOOGLE_CLIENT_ID`
**Required for Google sign-in.**

```
GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
```

Get this from Google Cloud Console → APIs & Services → Credentials → your OAuth
2.0 Client ID.

### `GOOGLE_CLIENT_SECRET`
**Required for Google sign-in.** Never commit this value.

```
GOOGLE_CLIENT_SECRET=your-client-secret
```

### `GOOGLE_REDIRECT_URI`
**Required for Google sign-in.** Must exactly match one of the Authorized Redirect
URIs registered in your Google Cloud Console OAuth credential.

```
# Local development
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback

# Production (add this URI in Google Cloud Console too)
# GOOGLE_REDIRECT_URI=https://your-backend-domain.com/auth/google/callback
```

A mismatch between this value and what is registered in Google Cloud Console will
cause a `redirect_uri_mismatch` error during the OAuth flow.

---

## Frontend / CORS

### `FRONTEND_URL`
**Required.** The URL of the frontend. The backend allows CORS requests only from
this origin — if it is wrong, the browser will block all API calls.

```
# Vite dev server (default)
FRONTEND_URL=http://localhost:5173

# Production
# FRONTEND_URL=https://your-app.vercel.app
```

Docker Compose overrides this automatically to `http://localhost:3000` — you do
not need to change it when running via `docker compose up`.

---

## F1 Season

### `F1_SEASON`
**Optional.** Default: `2026`. The F1 season used for standings, calendar, and
data sync endpoints.

```
F1_SEASON=2026
```

Change this value when a new season begins and you want the app to serve updated
data.

---

## Email

Both variables are required only if you want reminder and notification emails to
work. The app starts without them, but email sends will silently fail.

### `RESEND_API_KEY`
**Required for email.** API key from resend.com.

```
RESEND_API_KEY=re_your_api_key_here
```

Sign up at resend.com → API Keys → Create API Key. Never commit this value.

### `EMAIL_FROM`
**Required for email.** Sender name and address shown to recipients.

```
EMAIL_FROM=GridPulse <noreply@yourdomain.com>
```

The domain (`yourdomain.com`) must be verified on your Resend account before
emails will be delivered to arbitrary recipients. During local development you can
use `onboarding@resend.dev`, but Resend only allows sending to your own registered
email address with that shared domain.

---

## AI Race Assistant

All three variables are required only if you want the AI chat feature to work.
If `AI_API_KEY` is missing or invalid, the AI route returns an error but the rest
of the app continues to work.

### `AI_PROVIDER`
**Required for AI.** Default: `groq`. Which AI provider to use.

Supported values: `groq`, `anthropic`.

### `AI_API_KEY`
**Required for AI.** API key for the chosen provider. Never commit this value.

```
# Groq (free tier available)
AI_API_KEY=gsk_your_groq_api_key_here

# Anthropic (paid)
# AI_API_KEY=sk-ant-your-key-here
```

- Groq: console.groq.com → API Keys
- Anthropic: console.anthropic.com → API Keys

### `AI_MODEL`
**Optional.** Which model to call. Must be a model available on your chosen provider.

```
# Groq
AI_MODEL=llama-3.1-8b-instant        # fast, free tier
AI_MODEL=llama-3.3-70b-versatile     # higher quality

# Anthropic
AI_MODEL=claude-haiku-4-5-20251001   # fast, low cost
```

Default (Groq): `llama-3.1-8b-instant`.

---

## Frontend Variables (Vite)

These are set in `frontend/.env.local` for local frontend development, or in your
hosting dashboard (Vercel, Netlify) for production. They are not read from the
backend `.env` file.

### `VITE_API_URL`
**Required for frontend.** The base URL of the backend API. Vite bakes this into
the JavaScript bundle at build time.

```
# frontend/.env.local (for local development)
VITE_API_URL=http://localhost:8000

# Production: set in Vercel/Netlify dashboard
# VITE_API_URL=https://your-backend-domain.com
```

This value ends up in the compiled JavaScript and is visible to anyone who
inspects the browser's network requests — this is intentional and fine, it is just
a URL.

---

## Docker / Local Development

When running via `docker compose up`, the compose file sets these variables
automatically, overriding what is in `.env`:

| Variable | Docker Compose value | Why |
|---|---|---|
| `DATABASE_URL` | `postgresql://gridpulse:gridpulse@db:5432/gridpulse` | `db` is the service name, not `localhost` |
| `FRONTEND_URL` | `http://localhost:3000` | nginx serves the frontend on port 3000 |

You still need `.env` when using Docker Compose — the compose file reads it via
`env_file: .env` to pass secrets like `JWT_SECRET_KEY` to the backend container.
Only the two variables above are overridden.

---

## Quick Reference

### Minimum required to run locally (uvicorn + local Postgres)

| Variable | Notes |
|---|---|
| `DATABASE_URL` | Your local Postgres connection string |
| `JWT_SECRET_KEY` | Any random string locally — use `secrets.token_hex(32)` |
| `FRONTEND_URL` | `http://localhost:5173` |

Everything else is optional locally — the app starts without email, OAuth, or AI
keys; those features will return errors if used but won't break the server.

### Required in production (all features)

| Variable | Secret? |
|---|---|
| `DATABASE_URL` | Yes |
| `JWT_SECRET_KEY` | Yes |
| `FRONTEND_URL` | No |
| `GOOGLE_CLIENT_ID` | No |
| `GOOGLE_CLIENT_SECRET` | Yes |
| `GOOGLE_REDIRECT_URI` | No |
| `RESEND_API_KEY` | Yes |
| `EMAIL_FROM` | No |
| `AI_PROVIDER` | No |
| `AI_API_KEY` | Yes |
| `AI_MODEL` | No |
| `F1_SEASON` | No |

### Must never be committed to git

- `JWT_SECRET_KEY`
- `GOOGLE_CLIENT_SECRET`
- `RESEND_API_KEY`
- `AI_API_KEY`
- `DATABASE_URL` (contains your database password)

These all live in `.env`, which is listed in `.gitignore`.
