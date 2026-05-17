import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database.database import engine

print("Running migration: create ai_requests table...")

sql = text("""
    CREATE TABLE IF NOT EXISTS ai_requests (
        id           SERIAL PRIMARY KEY,
        user_id      INTEGER NOT NULL REFERENCES users(id),
        prompt       TEXT NOT NULL,
        response     TEXT,
        request_type VARCHAR NOT NULL DEFAULT 'general',
        tokens_used  INTEGER,
        model_name   VARCHAR,
        created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
    );
""")

with engine.connect() as conn:
    conn.execute(sql)
    conn.commit()

print("Done. ai_requests table created (or already existed — safe to run again).")
