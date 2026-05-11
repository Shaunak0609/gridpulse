import sys
import os
from datetime import date

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database.database import SessionLocal
from app.models import Team, Driver, Race, DriverStanding


def seed():
    db = SessionLocal()

    try:
        # --- Guard: skip if data already exists ---
        if db.query(Team).count() > 0:
            print("Database already has data. Skipping seed.")
            return

        # --- Teams ---
        print("Seeding teams...")

        red_bull  = Team(name="Red Bull Racing", constructor_name="Red Bull Racing", base="Milton Keynes, UK")
        mclaren   = Team(name="McLaren",         constructor_name="McLaren",         base="Woking, UK")
        ferrari   = Team(name="Ferrari",         constructor_name="Scuderia Ferrari", base="Maranello, Italy")
        mercedes  = Team(name="Mercedes",        constructor_name="Mercedes-AMG Petronas", base="Brackley, UK")

        db.add_all([red_bull, mclaren, ferrari, mercedes])
        db.flush()  # assigns IDs without committing yet

        # --- Drivers ---
        print("Seeding drivers...")

        verstappen = Driver(code="VER", full_name="Max Verstappen",  nationality="Dutch",      driver_number=1,  team_id=red_bull.id)
        norris     = Driver(code="NOR", full_name="Lando Norris",    nationality="British",    driver_number=4,  team_id=mclaren.id)
        leclerc    = Driver(code="LEC", full_name="Charles Leclerc", nationality="Monégasque", driver_number=16, team_id=ferrari.id)
        hamilton   = Driver(code="HAM", full_name="Lewis Hamilton",  nationality="British",    driver_number=44, team_id=ferrari.id)

        db.add_all([verstappen, norris, leclerc, hamilton])
        db.flush()

        # --- Races ---
        print("Seeding races...")

        bahrain   = Race(season=2025, round=1, name="Bahrain Grand Prix",       circuit_name="Bahrain International Circuit", country="Bahrain",      start_date=date(2025, 3, 2))
        saudi     = Race(season=2025, round=2, name="Saudi Arabian Grand Prix", circuit_name="Jeddah Street Circuit",         country="Saudi Arabia", start_date=date(2025, 3, 9))
        australia = Race(season=2025, round=3, name="Australian Grand Prix",    circuit_name="Albert Park Circuit",           country="Australia",    start_date=date(2025, 3, 16))

        db.add_all([bahrain, saudi, australia])
        db.flush()

        # --- Driver Standings ---
        print("Seeding driver standings...")

        standings = [
            DriverStanding(season=2025, driver_id=verstappen.id, team_id=red_bull.id, position=1, points=77, wins=3, podiums=3),
            DriverStanding(season=2025, driver_id=norris.id,     team_id=mclaren.id,  position=2, points=62, wins=1, podiums=2),
            DriverStanding(season=2025, driver_id=leclerc.id,    team_id=ferrari.id,  position=3, points=48, wins=0, podiums=1),
            DriverStanding(season=2025, driver_id=hamilton.id,   team_id=ferrari.id,  position=4, points=35, wins=0, podiums=1),
        ]

        db.add_all(standings)

        # --- Commit everything at once ---
        db.commit()
        print("Seed complete.")

    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}")
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed()
