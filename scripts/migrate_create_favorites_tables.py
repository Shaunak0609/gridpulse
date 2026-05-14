import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database.database import engine

print("Running migration: create favorite_drivers and favorite_teams tables...")

sql = text("""
    CREATE TABLE IF NOT EXISTS favorite_drivers (
        id         SERIAL PRIMARY KEY,
        user_id    INTEGER NOT NULL REFERENCES users(id),
        driver_id  INTEGER NOT NULL REFERENCES drivers(id),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT uq_favorite_driver_user UNIQUE (user_id, driver_id)
    );

    CREATE TABLE IF NOT EXISTS favorite_teams (
        id         SERIAL PRIMARY KEY,
        user_id    INTEGER NOT NULL REFERENCES users(id),
        team_id    INTEGER NOT NULL REFERENCES teams(id),
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        CONSTRAINT uq_favorite_team_user UNIQUE (user_id, team_id)
    );
""")

with engine.connect() as conn:
    conn.execute(sql)
    conn.commit()

print("Done. favorite_drivers and favorite_teams tables created (or already existed — safe to run again).")
