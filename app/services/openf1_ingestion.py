from datetime import datetime, timedelta

from sqlalchemy.orm import Session as DBSession

from app.models.lap import Lap
from app.models.race import Race
from app.models.race_control_message import RaceControlMessage
from app.models.session import Session as RaceSession
from app.models.stint import Stint
from app.models.weather_sample import WeatherSample
from app.services.openf1_client import (
    fetch_laps,
    fetch_race_control,
    fetch_session,
    fetch_stints,
    fetch_weather,
)

# Maps OpenF1's session_name to our internal session_type codes.
# OpenF1 uses "Practice 1" / "Practice 2" / "Practice 3" for practice sessions,
# and single words ("Race", "Qualifying") for others.
_SESSION_NAME_MAP: dict[str, str] = {
    "Practice 1": "fp1",
    "Practice 2": "fp2",
    "Practice 3": "fp3",
    "Qualifying": "qualifying",
    "Race": "race",
    "Sprint": "sprint",
    "Sprint Qualifying": "sprint_qualifying",
    "Sprint Shootout": "sprint_qualifying",  # alternate name used in 2023
}


def _parse_dt(value: str | None) -> datetime | None:
    """Parse an ISO 8601 string from OpenF1 into a timezone-aware datetime."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


# ─── Session linking ──────────────────────────────────────────────────────────

def link_session(session_key: int, db: DBSession) -> RaceSession | None:
    """
    Find the local Session row that corresponds to the given OpenF1 session_key
    and write the OpenF1 identifiers and metadata into it.

    Matching strategy:
      1. Fetch the OpenF1 session to get year, session_name, and date_start.
      2. Map session_name to our internal session_type (e.g. "Practice 1" → "fp1").
      3. Find the Race in our DB for that year whose start_date falls within
         4 days after the session's date — this covers Thursday practice sessions
         through Sunday race without ever crossing into the next race weekend.
      4. Find our local Session by race_id + session_type.
      5. Write openf1_session_key, openf1_meeting_key, circuit_short_name,
         and country_name into that row.

    Returns the linked session, or None if no match is found.
    """
    # Already linked — nothing to update.
    already = (
        db.query(RaceSession)
        .filter(RaceSession.openf1_session_key == session_key)
        .first()
    )
    if already:
        print(
            f"  Already linked — sessions.id={already.id} "
            f"({already.session_name})"
        )
        return already

    # Fetch session metadata from OpenF1.
    openf1_data = fetch_session(session_key)
    if not openf1_data:
        print(f"  OpenF1 returned no session for session_key={session_key}")
        return None

    year = openf1_data.get("year")
    session_name = openf1_data.get("session_name")
    session_type = _SESSION_NAME_MAP.get(session_name or "", "")
    date_start = _parse_dt(openf1_data.get("date_start"))

    if not year or not session_type or not date_start:
        print(
            f"  Cannot match: year={year!r}, session_name={session_name!r}, "
            f"date_start={openf1_data.get('date_start')!r}"
        )
        return None

    # Find the race whose start_date (race day) falls within 4 days after the
    # session date. This works for all session types across the weekend.
    session_date = date_start.date()
    race = (
        db.query(Race)
        .filter(
            Race.season == year,
            Race.start_date >= session_date,
            Race.start_date <= session_date + timedelta(days=4),
        )
        .first()
    )

    if not race:
        print(
            f"  No race found in our DB for year={year}, "
            f"session_date={session_date}. "
            f"Run 'python scripts/sync_f1_data.py' first."
        )
        return None

    # Find the matching session row.
    local_session = (
        db.query(RaceSession)
        .filter(
            RaceSession.race_id == race.id,
            RaceSession.session_type == session_type,
        )
        .first()
    )

    if not local_session:
        print(
            f"  No session found for race_id={race.id}, "
            f"session_type={session_type!r}. "
            f"Run 'python scripts/seed_sessions.py' first."
        )
        return None

    # Write the OpenF1 link fields.
    local_session.openf1_session_key = session_key
    local_session.openf1_meeting_key = openf1_data.get("meeting_key")
    local_session.circuit_short_name = openf1_data.get("circuit_short_name")
    local_session.country_name = openf1_data.get("country_name")
    db.commit()
    db.refresh(local_session)

    print(
        f"  Linked session_key={session_key} → sessions.id={local_session.id} "
        f"({race.name} — {local_session.session_name})"
    )
    return local_session


# ─── Laps ────────────────────────────────────────────────────────────────────

def ingest_laps(session_id: int, session_key: int, db: DBSession) -> dict:
    """
    Fetch all laps for a session from OpenF1 and insert rows that do not
    already exist (identified by session_id + driver_number + lap_number).

    Existing rows are left unchanged. Returns inserted and skipped counts.
    """
    raw = fetch_laps(session_key)
    if not raw:
        return {"inserted": 0, "skipped": 0}

    # Load existing (driver_number, lap_number) pairs into a set so we can
    # check membership in O(1) rather than querying once per row.
    existing: set[tuple[int, int]] = set(
        db.query(Lap.driver_number, Lap.lap_number)
        .filter(Lap.session_id == session_id)
        .all()
    )

    to_insert: list[Lap] = []
    skipped = 0

    for row in raw:
        driver_number = row.get("driver_number")
        lap_number = row.get("lap_number")

        if driver_number is None or lap_number is None:
            skipped += 1
            continue

        if (driver_number, lap_number) in existing:
            skipped += 1
            continue

        to_insert.append(
            Lap(
                session_id=session_id,
                driver_number=driver_number,
                lap_number=lap_number,
                lap_duration=row.get("lap_duration"),
                duration_sector_1=row.get("duration_sector_1"),
                duration_sector_2=row.get("duration_sector_2"),
                duration_sector_3=row.get("duration_sector_3"),
                is_pit_out_lap=bool(row.get("is_pit_out_lap", False)),
                date_start=_parse_dt(row.get("date_start")),
            )
        )

    if to_insert:
        db.bulk_save_objects(to_insert)
        db.commit()

    return {"inserted": len(to_insert), "skipped": skipped}


# ─── Stints ──────────────────────────────────────────────────────────────────

def ingest_stints(session_id: int, session_key: int, db: DBSession) -> dict:
    """
    Fetch all stints for a session and insert rows that do not already exist
    (identified by session_id + driver_number + stint_number).
    """
    raw = fetch_stints(session_key)
    if not raw:
        return {"inserted": 0, "skipped": 0}

    existing: set[tuple[int, int | None]] = set(
        db.query(Stint.driver_number, Stint.stint_number)
        .filter(Stint.session_id == session_id)
        .all()
    )

    to_insert: list[Stint] = []
    skipped = 0

    for row in raw:
        driver_number = row.get("driver_number")
        stint_number = row.get("stint_number")

        if driver_number is None:
            skipped += 1
            continue

        if (driver_number, stint_number) in existing:
            skipped += 1
            continue

        to_insert.append(
            Stint(
                session_id=session_id,
                driver_number=driver_number,
                stint_number=stint_number,
                compound=row.get("compound"),
                lap_start=row.get("lap_start"),
                lap_end=row.get("lap_end"),
                tyre_age_at_start=row.get("tyre_age_at_start"),
            )
        )

    if to_insert:
        db.bulk_save_objects(to_insert)
        db.commit()

    return {"inserted": len(to_insert), "skipped": skipped}


# ─── Race control messages ────────────────────────────────────────────────────

def ingest_race_control(session_id: int, session_key: int, db: DBSession) -> dict:
    """
    Fetch race control messages for a session.

    Because there is no reliable unique key on these messages (two messages
    can share the same timestamp in edge cases), this function clears all
    existing messages for the session and reinserts from OpenF1. The table
    is small (10–80 rows per session) so this is safe and fast.
    """
    raw = fetch_race_control(session_key)
    if not raw:
        return {"inserted": 0, "deleted": 0}

    deleted = (
        db.query(RaceControlMessage)
        .filter(RaceControlMessage.session_id == session_id)
        .delete()
    )
    db.commit()

    to_insert: list[RaceControlMessage] = []

    for row in raw:
        message_text = row.get("message") or ""
        if not message_text:
            continue
        to_insert.append(
            RaceControlMessage(
                session_id=session_id,
                date=_parse_dt(row.get("date")),
                lap_number=row.get("lap_number"),
                category=row.get("category"),
                message=message_text,
                flag=row.get("flag"),
                scope=row.get("scope"),
                sector=row.get("sector"),
                driver_number=row.get("driver_number"),
            )
        )

    if to_insert:
        db.bulk_save_objects(to_insert)
        db.commit()

    return {"inserted": len(to_insert), "deleted": deleted}


# ─── Weather samples ──────────────────────────────────────────────────────────

def ingest_weather(session_id: int, session_key: int, db: DBSession) -> dict:
    """
    Fetch weather samples for a session and insert rows that do not already
    exist (identified by session_id + date).

    OpenF1 returns rainfall as an integer (0 or 1) rather than a boolean.
    We convert it explicitly before storing.
    """
    raw = fetch_weather(session_key)
    if not raw:
        return {"inserted": 0, "skipped": 0}

    # Load existing timestamps so we can skip rows already in the database.
    existing_dates: set[datetime] = {
        row[0]
        for row in db.query(WeatherSample.date)
        .filter(WeatherSample.session_id == session_id)
        .all()
        if row[0] is not None
    }

    to_insert: list[WeatherSample] = []
    skipped = 0

    for row in raw:
        dt = _parse_dt(row.get("date"))
        if dt is None or dt in existing_dates:
            skipped += 1
            continue

        # OpenF1 sends rainfall as 0 / 1 (integer), not a Python bool.
        rainfall_raw = row.get("rainfall")
        rainfall = None if rainfall_raw is None else bool(rainfall_raw)

        to_insert.append(
            WeatherSample(
                session_id=session_id,
                date=dt,
                air_temperature=row.get("air_temperature"),
                track_temperature=row.get("track_temperature"),
                humidity=row.get("humidity"),
                rainfall=rainfall,
                wind_speed=row.get("wind_speed"),
                wind_direction=row.get("wind_direction"),
            )
        )

    if to_insert:
        db.bulk_save_objects(to_insert)
        db.commit()

    return {"inserted": len(to_insert), "skipped": skipped}
