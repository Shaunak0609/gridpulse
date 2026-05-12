import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import SessionLocal
from app.services.data_ingestion import sync_all


def main():
    db = SessionLocal()
    try:
        sync_all(db)
    except Exception as e:
        print(f"\nSync failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
