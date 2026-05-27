# ── Base image ────────────────────────────────────────────────────────────────
# python:3.14-slim gives us the same Python version used locally.
# "-slim" is a minimal Debian image — small but has the C libraries that
# psycopg2-binary needs (unlike "-alpine", which does not).
FROM python:3.14-slim

# ── Working directory ──────────────────────────────────────────────────────────
# All subsequent commands run inside /app inside the container.
WORKDIR /app

# ── Dependencies ───────────────────────────────────────────────────────────────
# Copy requirements.txt first, before the app code.
# Docker caches each instruction as a layer. Because requirements.txt changes
# less often than source code, this layer is reused on rebuilds unless the
# dependencies themselves change — keeping rebuilds fast.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Application code ───────────────────────────────────────────────────────────
# Copy only what the backend needs. .dockerignore excludes everything else
# (venv, node_modules, .env, frontend/dist, __pycache__, etc.).
COPY app/ ./app/
COPY scripts/ ./scripts/

# ── Port ───────────────────────────────────────────────────────────────────────
# Documents that the container listens on 8000. Does not publish the port —
# that happens when you run the container with -p 8000:8000.
EXPOSE 8000

# ── Startup command ────────────────────────────────────────────────────────────
# --host 0.0.0.0  → listen on all interfaces inside the container, not just
#                   localhost (the default), so traffic from outside can reach it.
# --port 8000     → match the EXPOSE above.
# No --reload     → that flag is for local development only; it adds overhead
#                   and is unnecessary in a container.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
