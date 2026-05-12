import sys
sys.path.append(".")

from app.services.f1_api_client import (
    fetch_race_calendar,
    fetch_driver_standings,
    fetch_constructor_standings,
)

races = fetch_race_calendar()
print(f"Races fetched: {len(races)}")
print("First race:", races[3]["raceName"], races[3]["date"])

standings = fetch_driver_standings()
print(f"\nDriver standings fetched: {len(standings)}")
print("P1:", standings[3]["Driver"]["familyName"], standings[3]["points"], "pts")

constructors = fetch_constructor_standings()
print(f"\nConstructor standings fetched: {len(constructors)}")
print("P1:", constructors[3]["Constructor"]["name"], constructors[3]["points"], "pts")