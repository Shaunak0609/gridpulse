"""
Sync historical OpenF1 data for one session into the local database.

Usage:
    # Sync a specific session by its OpenF1 session_key:
    python scripts/sync_openf1_session.py --session-key 9158

    # List all sessions for a year (to find the key you want):
    python scripts/sync_openf1_session.py --list 2024
"""

import argparse
import sys
from pathlib import Path

# Allow running from the repo root without installing the package.
sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from app.database.database import SessionLocal
from app.services.openf1_client import fetch_sessions
from app.services.openf1_ingestion import (
    ingest_laps,
    ingest_race_control,
    ingest_stints,
    ingest_weather,
    link_session,
)


def cmd_list(year: int) -> None:
    """Print all OpenF1 sessions for the given year."""
    sessions = fetch_sessions(year)
    if not sessions:
        print(f"No sessions found for {year}.")
        return

    print(f"\n{'session_key':<14} {'session_name':<22} {'circuit':<30} {'date_start'}")
    print("-" * 86)
    for s in sorted(sessions, key=lambda x: x.get("date_start") or ""):
        print(
            f"{s.get('session_key', ''):<14} "
            f"{s.get('session_name', ''):<22} "
            f"{s.get('circuit_short_name', ''):<30} "
            f"{s.get('date_start', '')}"
        )
    print(f"\n{len(sessions)} sessions listed.")


def cmd_sync(session_key: int) -> None:
    """Link and ingest all data for the given OpenF1 session_key."""
    db = SessionLocal()
    try:
        print(f"\n=== Syncing session_key={session_key} ===\n")

        # Step 1: Link the OpenF1 session to our local sessions table.
        print("Step 1/5 — Linking session...")
        local_session = link_session(session_key, db)
        if not local_session:
            print("\nCould not link session — aborting sync.")
            return

        session_id = local_session.id
        print(f"  session_id={session_id}\n")

        # Step 2: Weather samples.
        print("Step 2/5 — Ingesting weather samples...")
        weather = ingest_weather(session_id, session_key, db)
        print(f"  inserted={weather['inserted']}  skipped={weather['skipped']}\n")

        # Step 3: Race control messages.
        print("Step 3/5 — Ingesting race control messages...")
        rc = ingest_race_control(session_id, session_key, db)
        print(f"  inserted={rc['inserted']}  deleted(replaced)={rc['deleted']}\n")

        # Step 4: Stints.
        print("Step 4/5 — Ingesting stints...")
        stints = ingest_stints(session_id, session_key, db)
        print(f"  inserted={stints['inserted']}  skipped={stints['skipped']}\n")

        # Step 5: Laps.
        print("Step 5/5 — Ingesting laps...")
        laps = ingest_laps(session_id, session_key, db)
        print(f"  inserted={laps['inserted']}  skipped={laps['skipped']}\n")

        print("=== Sync complete ===")
        print(f"  Weather samples : {weather['inserted']} inserted")
        print(f"  Race control    : {rc['inserted']} inserted ({rc['deleted']} replaced)")
        print(f"  Stints          : {stints['inserted']} inserted")
        print(f"  Laps            : {laps['inserted']} inserted")

    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Sync OpenF1 historical data into the GridPulse database."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--session-key",
        type=int,
        metavar="KEY",
        help="OpenF1 session_key to sync (e.g. 9158)",
    )
    group.add_argument(
        "--list",
        type=int,
        metavar="YEAR",
        dest="list_year",
        help="List all OpenF1 sessions for YEAR (to find a session_key)",
    )

    args = parser.parse_args()

    if args.list_year:
        cmd_list(args.list_year)
    else:
        cmd_sync(args.session_key)


if __name__ == "__main__":
    main()
