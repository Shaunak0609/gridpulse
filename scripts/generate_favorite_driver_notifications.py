import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import SessionLocal
from app.services.favorite_driver_notifications import (
    generate_standing_notifications,
    generate_wins_notifications,
)


def _print_result(label: str, result: dict, tip_type: str) -> None:
    print(f"{label}")
    print(f"  Favourite drivers checked : {result['checked']}")
    print(f"  Notifications created     : {result['created']}")
    print(f"  Skipped (duplicate)       : {result['skipped_duplicate']}")
    print(f"  Skipped (no standing data): {result['skipped_no_standing']}")
    if 'skipped_no_wins' in result:
        print(f"  Skipped (no wins yet)     : {result['skipped_no_wins']}")
    print(f"  Skipped (opted out)       : {result['skipped_preference']}")
    print(f"  Emails sent               : {result['emails_sent']}")
    print(f"  Emails failed             : {result['emails_failed']}")
    if result['created'] == 0 and result['checked'] > 0:
        print(f"  Tip: all notifications already exist. Delete existing")
        print(f"  '{tip_type}' rows to regenerate them.")


def main() -> None:
    db = SessionLocal()
    try:
        standing_result = generate_standing_notifications(db)
        wins_result = generate_wins_notifications(db)

        print("Favourite-driver notifications — generation complete.")
        print()
        _print_result("Standing notifications:", standing_result, "favorite_driver_standing")
        print()
        _print_result("Wins notifications:", wins_result, "favorite_driver_wins")

    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
