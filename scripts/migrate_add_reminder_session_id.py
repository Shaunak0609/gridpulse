import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database.database import engine

print("Running migration: add session_id to reminders table...")

sql = text("""
    ALTER TABLE reminders
        ADD COLUMN IF NOT EXISTS session_id INTEGER REFERENCES sessions(id);
""")

with engine.connect() as conn:
    conn.execute(sql)
    conn.commit()

print("Done. session_id column added (or already existed — safe to run again).")
