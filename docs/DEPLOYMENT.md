# GridPulse Deployment Guide

This document covers what you need to know before deploying GridPulse to a public
hosting provider. The app is not deployed yet — this is a preparation reference.

For a full description of every environment variable and its default value, see
[docs/ENVIRONMENT.md](ENVIRONMENT.md).

---

## Recommended Architecture

GridPulse has three separate pieces to host:

| Piece | Recommended service | What it does |
|---|---|---|
| Backend (FastAPI) | Render, Railway, or Fly.io | Runs the Python API server |
| Frontend (React) | Vercel or Netlify | Serves the built static site |
| Database (PostgreSQL) | Render Postgres, Railway Postgres, or Supabase | Stores all app data |

You do not need Docker to deploy — Render and Railway can build directly from your
`requirements.txt`. Docker is an option if your host supports container deployments
(Fly.io and Railway both do).

---

## Backend Environment Variables

Set these in your hosting dashboard under Environment Variables (never in code).

### Required

| Variable | Example value | Notes |
|---|---|---|
| `DATABASE_URL` | `postgresql://user:pass@host:5432/gridpulse` | Provided by your database host |
| `JWT_SECRET_KEY` | `a64-char-random-hex-string` | Generate with `python -c "import secrets; print(secrets.token_hex(32))"` |
| `FRONTEND_URL` | `https://gridpulse.vercel.app` | Your deployed frontend URL — controls CORS |

### Required for Google OAuth

| Variable | Example value | Notes |
|---|---|---|
| `GOOGLE_CLIENT_ID` | `123456.apps.googleusercontent.com` | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | `GOCSPX-...` | From Google Cloud Console |
| `GOOGLE_REDIRECT_URI` | `https://gridpulse-api.onrender.com/auth/google/callback` | Must exactly match the URI registered in Google Cloud Console |

### Required for email

| Variable | Example value | Notes |
|---|---|---|
| `RESEND_API_KEY` | `re_...` | From resend.com |
| `EMAIL_FROM` | `GridPulse <noreply@yourdomain.com>` | Must be a verified sender domain on Resend |

### Required for AI

| Variable | Example value | Notes |
|---|---|---|
| `AI_PROVIDER` | `groq` or `anthropic` | Choose your provider |
| `AI_API_KEY` | `gsk_...` or `sk-ant-...` | From Groq or Anthropic console |
| `AI_MODEL` | `llama-3.1-8b-instant` | See `.env.example` for options |

### Optional

| Variable | Default | Notes |
|---|---|---|
| `JWT_ALGORITHM` | `HS256` | No need to change |
| `JWT_EXPIRE_MINUTES` | `60` | Token lifetime in minutes |
| `F1_SEASON` | `2026` | The F1 season to serve data for |

---

## Frontend Environment Variables

Vite bakes environment variables into the JavaScript bundle at build time, so these
must be set before the build runs — not at runtime.

| Variable | Example value | Notes |
|---|---|---|
| `VITE_API_URL` | `https://gridpulse-api.onrender.com` | Your deployed backend URL, no trailing slash |

On Vercel and Netlify, set this under **Project Settings → Environment Variables**
before triggering a deploy. The build will pick it up automatically.

---

## Database Setup

1. Create a PostgreSQL database on your chosen host.
2. Copy the connection string it gives you into `DATABASE_URL`.
3. Run migrations/table creation once after the backend starts for the first time.
   GridPulse uses SQLAlchemy — tables are created via `Base.metadata.create_all()`.
   Check whether your backend startup already does this, or whether you need to run
   it manually as a one-off command (e.g. `python -c "from app.database.database import Base, engine; Base.metadata.create_all(bind=engine)"`).
4. Seed local F1 data if needed (check `scripts/` for seed scripts).

The hosted database will start empty — you will need to seed it the same way you
seeded your local database.

---

## CORS Setup

GridPulse's backend allows requests only from the URL in `FRONTEND_URL`. If that
variable is wrong, your frontend will get CORS errors in the browser.

- Set `FRONTEND_URL` to your exact deployed frontend URL, e.g. `https://gridpulse.vercel.app`.
- No trailing slash.
- If Vercel gives you a preview URL on each deploy (e.g. `gridpulse-git-main-abc.vercel.app`),
  your main production domain will still work — but preview deploys will have CORS issues
  unless you also allow those origins. For now, keep it simple: use your primary domain.
- After updating `FRONTEND_URL` on the backend host, redeploy the backend for the
  change to take effect.

---

## Google OAuth — Production Redirect URI

The `GOOGLE_REDIRECT_URI` must be registered in Google Cloud Console or Google will
reject the OAuth flow with "redirect_uri_mismatch".

Steps:
1. Go to [Google Cloud Console](https://console.cloud.google.com) → APIs & Services → Credentials.
2. Open your OAuth 2.0 Client ID.
3. Under **Authorized redirect URIs**, add your production backend callback URL:
   `https://your-backend-domain.com/auth/google/callback`
4. Save and wait ~5 minutes for Google to propagate the change.
5. Set `GOOGLE_REDIRECT_URI` to that same URL in your hosting dashboard.

You can keep your local `http://localhost:8000/auth/google/callback` in the list
alongside the production URI — Google allows multiple redirect URIs.

---

## Email — Resend Domain Verification

Resend's free tier lets you send emails from `onboarding@resend.dev` but only to
your own email address. To send to any user in production:

1. Add and verify your own domain on resend.com → Domains.
2. Set `EMAIL_FROM` to an address on that domain, e.g. `GridPulse <noreply@yourdomain.com>`.
3. Set `RESEND_API_KEY` to a production API key (not a test key).

Until you verify a domain, notifications and reminder emails will not reach real users.

---

## AI API Key Notes

- **Groq** (default): Free tier available at console.groq.com. Rate limits apply — the
  `llama-3.1-8b-instant` model is fast and works well for race summaries.
- **Anthropic**: Paid. Use `claude-haiku-4-5-20251001` for cost efficiency.
- If `AI_API_KEY` is empty or wrong, the AI assistant route will return an error but
  the rest of the app continues to work normally.

---

## How Docker Helps Deployment

- **Consistency**: The same `Dockerfile` that runs locally will run identically on
  any host that supports containers (Fly.io, Railway, Render with Docker).
- **No Python version surprises**: The image pins Python 3.14-slim, so the host's
  installed Python version doesn't matter.
- **Fly.io** reads your `Dockerfile` directly — run `fly launch` from the repo root
  and it will build and deploy the backend image.
- **Railway** can also deploy from a Dockerfile or from `requirements.txt` — your
  choice.

For the frontend, Vercel and Netlify don't use Docker — they run `npm ci && npm run build`
directly. The `frontend/Dockerfile` is useful for self-hosted or container-based
deployments only.

---

## What Must Stay Secret

Never commit these to git or expose them in frontend code:

- `JWT_SECRET_KEY` — anyone with this key can forge login tokens
- `DATABASE_URL` — contains your database password
- `GOOGLE_CLIENT_SECRET` — allows impersonating your OAuth app
- `RESEND_API_KEY` — allows sending emails as you
- `AI_API_KEY` — billed to your account

The `.env` file is already in `.gitignore`. Double-check before pushing that you
have not accidentally hardcoded any of these values in source files.

`VITE_API_URL` is baked into the frontend bundle and is visible to anyone who
inspects the JavaScript — this is fine, it is just a URL, not a secret.

---

## Hosting Dashboard Checklist

Before going live, confirm each of these is set in your hosting provider's UI:

**Backend host (Render / Railway / Fly.io)**
- [ ] `DATABASE_URL`
- [ ] `JWT_SECRET_KEY`
- [ ] `FRONTEND_URL` (your production frontend URL)
- [ ] `GOOGLE_CLIENT_ID`
- [ ] `GOOGLE_CLIENT_SECRET`
- [ ] `GOOGLE_REDIRECT_URI`
- [ ] `RESEND_API_KEY`
- [ ] `EMAIL_FROM`
- [ ] `AI_PROVIDER`
- [ ] `AI_API_KEY`
- [ ] `AI_MODEL`

**Frontend host (Vercel / Netlify)**
- [ ] `VITE_API_URL` (your production backend URL)

**Google Cloud Console**
- [ ] Production redirect URI added to the OAuth credential

**Resend**
- [ ] Sending domain verified
