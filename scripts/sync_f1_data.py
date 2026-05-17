import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import SessionLocal
from app.services.data_ingestion import sync_all
from app.services.favorite_driver_notifications import (
    generate_standing_notifications,
    generate_wins_notifications,
)


def run_notifications(db) -> None:
    print("\n=== Favourite Driver Notifications ===")

    for label, generator, extra_skip_key in [
        ("Standing", generate_standing_notifications, None),
        ("Wins",     generate_wins_notifications,     "skipped_no_wins"),
    ]:
        print(f"\n[{label} Notifications]")
        try:
            result = generator(db)
            print(f"  Created                   : {result['created']}")
            print(f"  Skipped (duplicate)       : {result['skipped_duplicate']}")
            if extra_skip_key:
                print(f"  Skipped (no wins yet)     : {result[extra_skip_key]}")
            print(f"  Skipped (no standing data): {result['skipped_no_standing']}")
            print(f"  Skipped (opted out)       : {result['skipped_preference']}")
            if result['emails_sent'] or result['emails_failed']:
                print(f"  Emails sent               : {result['emails_sent']}")
                print(f"  Emails failed             : {result['emails_failed']}")
        except Exception as e:
            print(f"  ERROR: {e}")


def main():
    db = SessionLocal()
    try:
        print("Data sync started.")
        sync_all(db)
        print("\nData sync completed.")

        print("\nFavourite-driver notification generation started.")
        run_notifications(db)
    except Exception as e:
        print(f"\nSync failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
