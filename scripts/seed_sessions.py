import sys
import os
from datetime import datetime, timedelta, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import SessionLocal
from app.models.race import Race
from app.models.session import Session as RaceSession

# ---------------------------------------------------------------------------
# Session layout for a standard (non-sprint) race weekend.
#
# All offsets are relative to the race's start_date (Sunday) at 00:00 UTC.
# Times are approximate UTC values that look realistic across most circuits.
# ---------------------------------------------------------------------------
STANDARD_SESSIONS = [
    # (session_type, session_name, day_offset, hour, minute)
    ("fp1",        "Practice 1",  -2, 10, 30),
    ("fp2",        "Practice 2",  -2, 14,  0),
    ("fp3",        "Practice 3",  -1, 11, 30),
    ("qualifying", "Qualifying",  -1, 15,  0),
    ("race",       "Race",         0, 13,  0),
]


def _build_start_time(race: Race, day_offset: int, hour: int, minute: int) -> datetime:
    race_day = datetime(
        race.start_date.year,
        race.start_date.month,
        race.start_date.day,
        tzinfo=timezone.utc,
    )
    return race_day + timedelta(days=day_offset, hours=hour, minutes=minute)


def seed_sessions() -> None:
    db = SessionLocal()
    try:
        races = db.query(Race).order_by(Race.season, Race.round).all()

        if not races:
            print("No races found in the database. Run sync_f1_data.py first.")
            return

        print(f"Found {len(races)} race(s). Seeding sessions...")

        inserted = 0
        skipped = 0

        for race in races:
            for session_type, session_name, day_offset, hour, minute in STANDARD_SESSIONS:
                existing = (
                    db.query(RaceSession)
                    .filter_by(race_id=race.id, session_type=session_type)
                    .first()
                )
                if existing:
                    skipped += 1
                    continue

                session = RaceSession(
                    race_id=race.id,
                    session_type=session_type,
                    session_name=session_name,
                    start_time=_build_start_time(race, day_offset, hour, minute),
                    end_time=None,
                    timezone=None,
                )
                db.add(session)
                inserted += 1

        db.commit()
        print(f"Done. {inserted} session(s) inserted, {skipped} already existed.")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_sessions()
