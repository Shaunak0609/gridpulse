import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database.database import engine

print("Running migration: add email preference columns to users table...")

sql = text("""
    ALTER TABLE users
        ADD COLUMN IF NOT EXISTS email_notifications_enabled          BOOLEAN NOT NULL DEFAULT false,
        ADD COLUMN IF NOT EXISTS calendar_email_reminders_enabled     BOOLEAN NOT NULL DEFAULT false,
        ADD COLUMN IF NOT EXISTS favorite_driver_email_alerts_enabled BOOLEAN NOT NULL DEFAULT false;
""")

with engine.connect() as conn:
    conn.execute(sql)
    conn.commit()

print("Done. Columns added (or already existed — safe to run again).")
