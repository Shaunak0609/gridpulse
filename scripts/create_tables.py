import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import engine, Base
from app.models import Team, Driver, Race, DriverStanding, User, Reminder, Notification, Session, FavoriteDriver, FavoriteTeam, AIRequest, Lap, Stint, RaceControlMessage, WeatherSample

print("Creating tables...")

Base.metadata.create_all(bind=engine)

print("Done. Tables created:")
for table in Base.metadata.tables:
    print(f"  - {table}")
