import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database.database import engine

print("Running migration: create OpenF1 historical data tables...")

# Each CREATE TABLE uses IF NOT EXISTS and each constraint uses IF NOT EXISTS
# (via the index form) so this script is safe to run more than once.
#
# Tables created:
#   laps                  — per-lap timing and sector splits
#   stints                — tyre compound and stint lap ranges
#   race_control_messages — steward/race director messages (safety car, flags, etc.)
#   weather_samples       — air/track temperature, humidity, rainfall per session

sql = text("""
    -- ── Laps ─────────────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS laps (
        id               SERIAL PRIMARY KEY,
        session_id       INTEGER NOT NULL REFERENCES sessions(id),
        driver_number    INTEGER NOT NULL,
        lap_number       INTEGER NOT NULL,
        lap_duration     FLOAT,
        duration_sector_1 FLOAT,
        duration_sector_2 FLOAT,
        duration_sector_3 FLOAT,
        is_pit_out_lap   BOOLEAN NOT NULL DEFAULT FALSE,
        date_start       TIMESTAMPTZ,
        CONSTRAINT uq_lap_session_driver_lap
            UNIQUE (session_id, driver_number, lap_number)
    );

    -- ── Stints ───────────────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS stints (
        id               SERIAL PRIMARY KEY,
        session_id       INTEGER NOT NULL REFERENCES sessions(id),
        driver_number    INTEGER NOT NULL,
        stint_number     INTEGER,
        compound         VARCHAR,
        lap_start        INTEGER,
        lap_end          INTEGER,
        tyre_age_at_start INTEGER,
        CONSTRAINT uq_stint_session_driver_stint
            UNIQUE (session_id, driver_number, stint_number)
    );

    -- ── Race control messages ─────────────────────────────────────────────────
    -- No unique constraint — multiple messages can share the same timestamp.
    -- Deduplication is handled at the ingestion layer (clear + reinsert per session).
    CREATE TABLE IF NOT EXISTS race_control_messages (
        id            SERIAL PRIMARY KEY,
        session_id    INTEGER NOT NULL REFERENCES sessions(id),
        date          TIMESTAMPTZ,
        lap_number    INTEGER,
        category      VARCHAR,
        message       TEXT NOT NULL,
        flag          VARCHAR,
        scope         VARCHAR,
        sector        INTEGER,
        driver_number INTEGER
    );

    -- ── Weather samples ───────────────────────────────────────────────────────
    CREATE TABLE IF NOT EXISTS weather_samples (
        id                SERIAL PRIMARY KEY,
        session_id        INTEGER NOT NULL REFERENCES sessions(id),
        date              TIMESTAMPTZ,
        air_temperature   FLOAT,
        track_temperature FLOAT,
        humidity          FLOAT,
        rainfall          BOOLEAN,
        wind_speed        FLOAT,
        wind_direction    INTEGER,
        CONSTRAINT uq_weather_session_date
            UNIQUE (session_id, date)
    );
""")

with engine.connect() as conn:
    conn.execute(sql)
    conn.commit()

print("Done. Tables created (or already existed — safe to run again):")
print("  laps")
print("  stints")
print("  race_control_messages")
print("  weather_samples")
