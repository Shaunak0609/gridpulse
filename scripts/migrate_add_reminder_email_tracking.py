import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database.database import engine

print("Running migration: add email tracking columns to reminders table...")

sql = text("""
    ALTER TABLE reminders
        ADD COLUMN IF NOT EXISTS email_sent    BOOLEAN                  NOT NULL DEFAULT false,
        ADD COLUMN IF NOT EXISTS email_sent_at TIMESTAMP WITH TIME ZONE          DEFAULT NULL;
""")

with engine.connect() as conn:
    conn.execute(sql)
    conn.commit()

print("Done. Columns added (or already existed — safe to run again).")
