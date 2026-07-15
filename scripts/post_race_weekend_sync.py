"""
Post-race-weekend sync for GridPulse.

Run this after each F1 race weekend (for example weekly, via a Render Cron Job)
to keep the app's data current. It reuses the existing sync services rather than
duplicating their logic:

  1. Refresh teams, drivers, the race calendar, the session schedule, and
     driver standings from Jolpica  -> app.services.data_ingestion.sync_all()
  2. Detect race weekends whose race day has already passed, from the races
     table (DB-driven, no reliance on "it must be Monday").
  3. For each completed weekend, ingest detailed results (laps, stints,
     weather, race control) for the sessions that have *finished* and are not
     yet linked to OpenF1  -> app.services.openf1_ingestion.*

Idempotent / safe to run repeatedly
-----------------------------------
  * sync_all() upserts (update-or-insert) — it never creates duplicate teams,
    drivers, races, sessions, or standings.
  * A session's detail data is considered "already synced" when its
    sessions.openf1_session_key column is set. Such sessions are skipped, so a
    re-run does no redundant OpenF1 fetching.
  * Within a weekend, only OpenF1 sessions whose date_end is in the past are
    ingested, so an in-progress session is never half-synced. This also handles
    weekends that finish in different time zones — completion is read from the
    actual session end timestamps, not the calendar weekday.
  * Nothing is deleted. User-created reminders, favourites, notification
    preferences, and accounts are never touched by this script.

No new database columns are required: sync status is derived from the existing
sessions.openf1_session_key column, which avoids a schema migration on the live
database.

Usage (identical locally and on Render):
    python scripts/post_race_weekend_sync.py
    python scripts/post_race_weekend_sync.py --season 2026
    python scripts/post_race_weekend_sync.py --with-alerts   # also generate favourite-driver alerts for newly synced sessions

Environment:
    Uses the existing DATABASE_URL (and optional F1_SEASON) from the environment
    / .env. No database URL is hardcoded.
"""

import argparse
import logging
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Allow running from the repo root without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.database.database import SessionLocal
from app.models.race import Race
from app.models.session import Session as RaceSession
from app.services.data_ingestion import sync_all
from app.services.f1_api_client import SEASON
from app.services.favorite_driver_alerts import generate_session_alerts
from app.services.openf1_client import fetch_sessions
from app.services.openf1_ingestion import (
    ingest_laps,
    ingest_race_control,
    ingest_stints,
    ingest_weather,
    link_session,
)

# Logging is configured to stdout with timestamps so the output is readable in
# Render's log viewer. The reused services use print() — those lines also reach
# stdout and interleave fine.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    stream=sys.stdout,
)
log = logging.getLogger("post_race_sync")


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except (ValueError, TypeError):
        return None


def _sync_session_detail(session_key: int, db, with_alerts: bool) -> dict:
    """
    Link one finished OpenF1 session to its local session and ingest detail
    data. Reuses the openf1_ingestion service functions — each of which skips
    rows that already exist, so this is safe to call more than once.
    """
    local = link_session(session_key, db)
    if not local:
        return {"linked": False}

    sid = local.id
    weather = ingest_weather(sid, session_key, db)
    rc = ingest_race_control(sid, session_key, db)
    stints = ingest_stints(sid, session_key, db)
    laps = ingest_laps(sid, session_key, db)

    summary = {
        "linked": True,
        "session_id": sid,
        "session_name": local.session_name,
        "weather": weather["inserted"],
        "race_control": rc["inserted"],
        "stints": stints["inserted"],
        "laps": laps["inserted"],
    }

    if with_alerts:
        try:
            result = generate_session_alerts(sid, db)
            if "error" in result:
                log.warning("    Alert generation error: %s", result["error"])
            elif result.get("is_synced", True):
                summary["alerts_created"] = result.get("total_created", 0)
                log.info(
                    "    Favourite-driver alerts: %s created, %s duplicate skipped",
                    result.get("total_created", 0),
                    result.get("total_skipped", 0),
                )
        except Exception as e:  # noqa: BLE001 - alert failure must not abort the data sync
            log.warning("    Alert generation failed (sync data is still saved): %s", e)

    return summary


def run_sync(season: int, with_alerts: bool) -> int:
    """
    Returns the number of errors encountered. 0 means a fully clean run.

    Errors are non-fatal to the rest of the run (Phase 1 is already committed and
    other sessions still process), but a non-zero return lets the caller exit
    non-zero so Render marks the cron run as failed.
    """
    log.info("=== GridPulse post-race-weekend sync started (season=%s) ===", season)

    errors = 0
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        today = now.date()

        # ── Phase 1: calendar / standings / schedule refresh (idempotent) ──────
        log.info(
            "Phase 1 — refreshing teams, drivers, calendar, sessions, and "
            "driver standings from Jolpica..."
        )
        sync_all(db)

        # ── Phase 2: completed race weekend detail sync ────────────────────────
        completed_races = (
            db.query(Race)
            .filter(Race.season == season, Race.start_date.isnot(None))
            .filter(Race.start_date <= today)
            .order_by(Race.round)
            .all()
        )
        log.info(
            "Phase 2 — %s race weekend(s) in %s have a race day on or before today.",
            len(completed_races),
            season,
        )
        if not completed_races:
            log.info("No completed race weekends yet. Nothing to sync.")
            log.info("=== Sync complete: 0 sessions synced ===")
            return errors

        # Sessions whose detail data is already synced (openf1_session_key set).
        linked_keys: set[int] = {
            key
            for (key,) in db.query(RaceSession.openf1_session_key)
            .filter(RaceSession.openf1_session_key.isnot(None))
            .all()
            if key is not None
        }

        try:
            openf1_sessions = fetch_sessions(season)
        except RuntimeError as e:
            log.error("Could not fetch OpenF1 sessions: %s", e)
            log.error("Phase 1 standings/calendar refresh succeeded; detail sync skipped.")
            return errors + 1

        # Index OpenF1 sessions by their start date for matching to races.
        for s in openf1_sessions:
            s["_date_start"] = _parse_dt(s.get("date_start"))
            s["_date_end"] = _parse_dt(s.get("date_end"))

        total_new = 0

        for race in completed_races:
            log.info("Checking weekend: %s (round %s, %s)", race.name, race.round, race.start_date)

            # A session belongs to this weekend if its date falls in the four
            # days up to and including race day (mirrors link_session matching).
            window_start = race.start_date - timedelta(days=4)
            weekend_sessions = [
                s
                for s in openf1_sessions
                if s["_date_start"] is not None
                and window_start <= s["_date_start"].date() <= race.start_date
            ]
            weekend_sessions.sort(key=lambda s: s["_date_start"])

            if not weekend_sessions:
                log.info("  No OpenF1 sessions found for this weekend yet.")
                continue

            synced_here = 0
            for s in weekend_sessions:
                key = s.get("session_key")
                name = s.get("session_name", "?")
                end = s["_date_end"]

                if key in linked_keys:
                    log.info("  '%s' already synced (skipping).", name)
                    continue

                if end is None or end >= now:
                    log.info("  '%s' not finished yet (skipping).", name)
                    continue

                log.info("  Syncing '%s' (OpenF1 session_key=%s)...", name, key)
                try:
                    result = _sync_session_detail(key, db, with_alerts)
                except Exception as e:  # noqa: BLE001 - keep going with other sessions
                    db.rollback()
                    errors += 1
                    log.error("  Failed to sync '%s' (session_key=%s): %s", name, key, e)
                    continue

                if not result.get("linked"):
                    log.warning(
                        "  Could not link '%s' (session_key=%s) to a local session.",
                        name,
                        key,
                    )
                    continue

                log.info(
                    "    Synced: laps=%s stints=%s weather=%s race_control=%s",
                    result["laps"],
                    result["stints"],
                    result["weather"],
                    result["race_control"],
                )
                linked_keys.add(key)
                synced_here += 1
                total_new += 1

            if synced_here == 0:
                log.info("  Nothing new to sync for this weekend.")

        if total_new == 0:
            log.info("Phase 2 — no new finished sessions needed syncing.")
        else:
            log.info("Phase 2 — synced detail data for %s new session(s).", total_new)

        log.info("Leaderboards/standings refreshed via Phase 1; "
                 "Dashboard, Strategy, Analytics, Calendar, and Leaderboards now read the latest data.")
        log.info(
            "=== Sync complete: %s session(s) synced, %s error(s) ===",
            total_new,
            errors,
        )
        return errors

    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync completed F1 race weekends into the GridPulse database."
    )
    parser.add_argument(
        "--season",
        type=int,
        default=SEASON,
        help=f"F1 season to sync (default: {SEASON}, from F1_SEASON env).",
    )
    parser.add_argument(
        "--with-alerts",
        action="store_true",
        help="Also generate favourite-driver alerts for newly synced sessions "
             "(may send emails). Off by default so the cron has no email side effects.",
    )
    args = parser.parse_args()

    try:
        errors = run_sync(args.season, args.with_alerts)
    except Exception as e:  # noqa: BLE001 - surface a clean non-zero exit for Render
        log.exception("Post-race-weekend sync failed: %s", e)
        sys.exit(1)

    if errors:
        # Phase 1 work is committed; some detail sync failed. Exit non-zero so
        # Render flags the run, but the next scheduled run will retry idempotently.
        sys.exit(1)


if __name__ == "__main__":
    main()
