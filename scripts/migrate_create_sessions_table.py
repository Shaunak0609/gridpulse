import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database.database import engine

print("Running migration: create sessions table...")

sql = text("""
    CREATE TABLE IF NOT EXISTS sessions (
        id          SERIAL PRIMARY KEY,
        race_id     INTEGER NOT NULL REFERENCES races(id),
        session_type TEXT    NOT NULL,
        session_name TEXT    NOT NULL,
        start_time  TIMESTAMPTZ,
        end_time    TIMESTAMPTZ,
        timezone    TEXT,
        created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT uq_session_race_type UNIQUE (race_id, session_type)
    );
""")

with engine.connect() as conn:
    conn.execute(sql)
    conn.commit()

print("Done. sessions table created (or already existed — safe to run again).")
