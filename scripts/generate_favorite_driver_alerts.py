"""
Generates favourite-driver session alerts for a specific session.

Usage
-----
List all synced sessions (shows session IDs to use with --session-id):

    python scripts/generate_favorite_driver_alerts.py --list

Generate alerts for one session:

    python scripts/generate_favorite_driver_alerts.py --session-id 5

Running the script more than once for the same session is safe. Alerts that
already exist are counted as duplicates and skipped — no duplicate notifications
are created.

Prerequisites
-------------
1. Run the migration to add the related_session_id column:

       python scripts/migrate_add_notification_session_id.py

2. Sync OpenF1 data for the session you want alerts for:

       python scripts/sync_openf1_session.py --session-key <key>

3. Have at least one user account with a favourited driver.
"""

import argparse
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import SessionLocal
from app.models.session import Session as RaceSession
from app.services.favorite_driver_alerts import _ALL_ALERT_TYPES, generate_session_alerts

# Human-readable labels for each alert type, used in printed output.
_ALERT_LABELS = {
    "favorite_driver_fastest_lap": "Fastest lap in session",
    "favorite_driver_strategy":    "Strategy summary",
    "favorite_driver_rc_mention":  "Race control mention",
    "favorite_driver_lap_comparison": "Lap data note",
}


def _print_synced_sessions(db) -> None:
    """Print all sessions that have been linked to an OpenF1 session key."""
    sessions = (
        db.query(RaceSession)
        .filter(RaceSession.openf1_session_key.isnot(None))
        .order_by(RaceSession.start_time.desc())
        .all()
    )

    if not sessions:
        print("No synced sessions found.")
        print("Run: python scripts/sync_openf1_session.py --session-key <key>")
        return

    print(f"{'ID':<6} {'Session':<18} {'Race':<40} {'OpenF1 key'}")
    print("-" * 80)
    for s in sessions:
        race_name = s.race.name if s.race else "Unknown"
        print(
            f"{s.id:<6} {s.session_name:<18} {race_name:<40} {s.openf1_session_key}"
        )
    print()
    print(f"Found {len(sessions)} synced session(s).")
    print("Use --session-id <ID> from the first column to generate alerts.")


def _print_result(result: dict) -> None:
    """Print the generation summary in a readable format."""

    # Not-synced or not-found cases return a lightweight dict.
    if not result.get("is_synced", True):
        print(f"  Session ID    : {result.get('session_id', '?')}")
        print(f"  Session name  : {result.get('session_name', '?')}")
        print(f"  Status        : not synced")
        print(f"  {result.get('message', '')}")
        return

    if "error" in result:
        print(f"  Error: {result['error']}")
        return

    session_label = f"{result.get('race_name', '')} — {result.get('session_name', '')}".strip(" —")
    print(f"  Session       : {session_label} (id={result['session_id']})")
    print(f"  Drivers with data checked : {result['favorite_drivers_checked']}")
    print()

    alerts = result.get("alerts", {})
    any_created = result["total_created"] > 0
    any_skipped = result["total_skipped"] > 0

    for alert_type in _ALL_ALERT_TYPES:
        counts = alerts.get(alert_type, {"created": 0, "skipped": 0, "emails_sent": 0, "emails_failed": 0})
        label = _ALERT_LABELS.get(alert_type, alert_type)
        print(f"  [{label}]")
        print(f"    Created          : {counts['created']}")
        print(f"    Skipped (dup)    : {counts['skipped']}")
        print(f"    Emails sent      : {counts['emails_sent']}")
        if counts["emails_failed"]:
            print(f"    Emails failed    : {counts['emails_failed']}")

    print()
    print(f"  Total created  : {result['total_created']}")
    print(f"  Total skipped  : {result['total_skipped']}")
    print(f"  Emails sent    : {result['emails_sent']}")
    if result["emails_failed"]:
        print(f"  Emails failed  : {result['emails_failed']}")

    if not any_created and any_skipped:
        print()
        print("  Tip: all alerts already exist for this session.")
        print("  To regenerate, delete the existing notifications from psql:")
        print(f"    DELETE FROM notifications")
        print(f"    WHERE related_session_id = {result['session_id']}")
        print(f"      AND type LIKE 'favorite_driver_%';")

    if not any_created and not any_skipped:
        print()
        print("  No alerts were generated.")
        print("  This usually means no users have favourited a driver")
        print("  who has lap, stint, or race control data in this session.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate favourite-driver alerts from stored OpenF1 session data.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python scripts/generate_favorite_driver_alerts.py --list\n"
            "  python scripts/generate_favorite_driver_alerts.py --session-id 5\n"
        ),
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all synced sessions with their IDs and exit.",
    )
    parser.add_argument(
        "--session-id",
        type=int,
        metavar="ID",
        help="GridPulse session ID to generate alerts for.",
    )
    args = parser.parse_args()

    if not args.list and args.session_id is None:
        parser.print_help()
        sys.exit(0)

    db = SessionLocal()
    try:
        if args.list:
            _print_synced_sessions(db)
            return

        session_id = args.session_id
        print(f"=== Favourite-driver session alerts — session_id={session_id} ===")
        print()

        result = generate_session_alerts(session_id, db)
        _print_result(result)

    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
