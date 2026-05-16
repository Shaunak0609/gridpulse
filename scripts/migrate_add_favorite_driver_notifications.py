import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database.database import engine

print("Running migration: add favorite_driver_notifications_enabled to users table...")

sql = text("""
    ALTER TABLE users
        ADD COLUMN IF NOT EXISTS favorite_driver_notifications_enabled BOOLEAN NOT NULL DEFAULT true;
""")

with engine.connect() as conn:
    conn.execute(sql)
    conn.commit()

print("Done. Column added (or already existed — safe to run again).")
print("  Default: true — existing users will receive in-app driver notifications unless they opt out.")
