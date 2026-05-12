from datetime import date

from sqlalchemy.orm import Session

from app.models.driver import Driver
from app.models.race import Race
from app.models.standing import DriverStanding
from app.models.team import Team
from app.services.f1_api_client import (
    SEASON,
    fetch_constructor_standings,
    fetch_driver_standings,
    fetch_race_calendar,
)


def sync_teams(db: Session) -> None:
    print("Syncing teams...")

    constructor_standings = fetch_constructor_standings()

    for entry in constructor_standings:
        c = entry["Constructor"]
        jolpica_ref = c["constructorId"]   # e.g. "red_bull", "mclaren"
        name = c["name"]                   # e.g. "Red Bull", "McLaren"

        team = db.query(Team).filter(Team.jolpica_ref == jolpica_ref).first()

        if team:
            team.name = name
            team.constructor_name = name
        else:
            team = Team(
                jolpica_ref=jolpica_ref,
                name=name,
                constructor_name=name,
                base=None,
            )
            db.add(team)

    db.commit()
    print(f"  Done. {len(constructor_standings)} teams synced.")


def sync_drivers(db: Session) -> None:
    print("Syncing drivers...")

    driver_standings = fetch_driver_standings()
    count = 0

    for entry in driver_standings:
        d = entry["Driver"]
        jolpica_ref = d["driverId"]                              # e.g. "max_verstappen"
        code = d.get("code", "")                                 # e.g. "VER"
        full_name = f"{d['givenName']} {d['familyName']}"        # e.g. "Max Verstappen"
        nationality = d.get("nationality")
        number_str = d.get("permanentNumber")
        driver_number = int(number_str) if number_str else None

        # Find this driver's team using the constructor reference
        team = None
        constructors = entry.get("Constructors", [])
        if constructors:
            constructor_ref = constructors[0]["constructorId"]
            team = db.query(Team).filter(Team.jolpica_ref == constructor_ref).first()

        driver = db.query(Driver).filter(Driver.jolpica_ref == jolpica_ref).first()

        if driver:
            driver.code = code
            driver.full_name = full_name
            driver.nationality = nationality
            driver.driver_number = driver_number
            driver.team_id = team.id if team else driver.team_id
        else:
            driver = Driver(
                jolpica_ref=jolpica_ref,
                code=code,
                full_name=full_name,
                nationality=nationality,
                driver_number=driver_number,
                team_id=team.id if team else None,
            )
            db.add(driver)

        count += 1

    db.commit()
    print(f"  Done. {count} drivers synced.")


def sync_race_calendar(db: Session) -> None:
    print("Syncing race calendar...")

    races = fetch_race_calendar()

    for race_data in races:
        season = int(race_data["season"])
        round_num = int(race_data["round"])
        name = race_data["raceName"]
        circuit = race_data.get("Circuit", {})
        circuit_name = circuit.get("circuitName")
        country = circuit.get("Location", {}).get("country")
        date_str = race_data.get("date")
        start_date = date.fromisoformat(date_str) if date_str else None

        race = db.query(Race).filter(
            Race.season == season,
            Race.round == round_num,
        ).first()

        if race:
            race.name = name
            race.circuit_name = circuit_name
            race.country = country
            race.start_date = start_date
        else:
            race = Race(
                season=season,
                round=round_num,
                name=name,
                circuit_name=circuit_name,
                country=country,
                start_date=start_date,
            )
            db.add(race)

    db.commit()
    print(f"  Done. {len(races)} races synced.")


def sync_driver_standings(db: Session) -> None:
    print("Syncing driver standings...")

    driver_standings = fetch_driver_standings()
    count = 0

    for entry in driver_standings:
        jolpica_ref = entry["Driver"]["driverId"]
        position = int(entry["position"])
        points = float(entry["points"])
        wins = int(entry["wins"])

        driver = db.query(Driver).filter(Driver.jolpica_ref == jolpica_ref).first()
        if not driver:
            print(f"  Warning: driver '{jolpica_ref}' not found in DB, skipping.")
            continue

        team = None
        constructors = entry.get("Constructors", [])
        if constructors:
            team = db.query(Team).filter(
                Team.jolpica_ref == constructors[0]["constructorId"]
            ).first()

        standing = db.query(DriverStanding).filter(
            DriverStanding.season == SEASON,
            DriverStanding.driver_id == driver.id,
        ).first()

        if standing:
            standing.position = position
            standing.points = points
            standing.wins = wins
            standing.team_id = team.id if team else standing.team_id
        else:
            standing = DriverStanding(
                season=SEASON,
                driver_id=driver.id,
                team_id=team.id if team else None,
                position=position,
                points=points,
                wins=wins,
                podiums=0,
            )
            db.add(standing)

        count += 1

    db.commit()
    print(f"  Done. {count} driver standings synced.")


def sync_all(db: Session) -> None:
    print(f"Starting full F1 data sync for {SEASON} season...\n")
    sync_teams(db)
    sync_drivers(db)
    sync_race_calendar(db)
    sync_driver_standings(db)
    print("\nAll done.")
