import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from app.database.database import engine

print("Running migration: add OpenF1 link fields to sessions table...")

# Each statement uses ADD COLUMN IF NOT EXISTS so the script is safe to run
# more than once. Existing session rows are unaffected — all new columns are
# nullable and default to NULL.
#
# The unique index on openf1_session_key is partial (WHERE openf1_session_key
# IS NOT NULL) so that many rows can stay NULL while the constraint still
# prevents two rows from being linked to the same OpenF1 session.

sql = text("""
    ALTER TABLE sessions
        ADD COLUMN IF NOT EXISTS openf1_session_key  INTEGER,
        ADD COLUMN IF NOT EXISTS openf1_meeting_key  INTEGER,
        ADD COLUMN IF NOT EXISTS circuit_short_name  VARCHAR,
        ADD COLUMN IF NOT EXISTS country_name        VARCHAR;

    CREATE UNIQUE INDEX IF NOT EXISTS uix_sessions_openf1_session_key
        ON sessions (openf1_session_key)
        WHERE openf1_session_key IS NOT NULL;
""")

with engine.connect() as conn:
    conn.execute(sql)
    conn.commit()

print("Done. Columns added (or already present — safe to run again):")
print("  sessions.openf1_session_key  INTEGER  NULLABLE  UNIQUE (partial)")
print("  sessions.openf1_meeting_key  INTEGER  NULLABLE")
print("  sessions.circuit_short_name  VARCHAR  NULLABLE")
print("  sessions.country_name        VARCHAR  NULLABLE")
