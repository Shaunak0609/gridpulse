import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import SessionLocal
from app.services.favorite_driver_notifications import generate_standing_notifications


def main() -> None:
    db = SessionLocal()
    try:
        result = generate_standing_notifications(db)

        print(f"Favourite-driver notifications — generation complete.")
        print(f"  Favourite drivers checked : {result['checked']}")
        print(f"  Notifications created     : {result['created']}")
        print(f"  Skipped (duplicate)       : {result['skipped_duplicate']}")
        print(f"  Skipped (no standing data): {result['skipped_no_standing']}")
        print(f"  Skipped (opted out)       : {result['skipped_preference']}")

        if result['created'] == 0 and result['checked'] > 0:
            print()
            print("Tip: all notifications already exist. Delete existing")
            print("'favorite_driver_standing' rows to regenerate them.")

    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
