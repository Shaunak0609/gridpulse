"""
Adds a nullable related_session_id foreign key to the notifications table.

This column is used by Phase 15 favourite-driver session alerts to link a
notification to a specific session and to enforce the one-notification-per
(user, alert_type, driver, session) dedup rule.

Safe to run on an existing database — ADD COLUMN IF NOT EXISTS is a no-op when
the column already exists. Fresh databases created with create_tables.py get the
column automatically once the Notification model is updated.
"""

import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text

from app.database.database import engine


def migrate() -> None:
    with engine.connect() as conn:
        print("Running migration: add related_session_id to notifications...")
        conn.execute(text("""
            ALTER TABLE notifications
            ADD COLUMN IF NOT EXISTS related_session_id INTEGER
            REFERENCES sessions(id) ON DELETE SET NULL;
        """))
        conn.commit()
        print("Done. related_session_id added (or already existed — safe to run again).")


if __name__ == "__main__":
    migrate()
