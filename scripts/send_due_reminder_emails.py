import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import SessionLocal
from app.services.reminder_email_service import process_due_reminders


def main() -> None:
    db = SessionLocal()
    try:
        result = process_due_reminders(db)
        print(f"Found {result['total']} due reminder(s).")
        print(f"Sent: {result['sent']}  Failed: {result['failed']}")
    except Exception as e:
        print(f"Error: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
