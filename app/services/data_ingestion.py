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


def sync_teams(db: Session) -> bool:
    print("\n[Teams]")

    try:
        constructor_standings = fetch_constructor_standings()
    except RuntimeError as e:
        print(f"  ERROR fetching teams from Jolpica: {e}")
        return False

    if not constructor_standings:
        print("  WARNING: Jolpica returned 0 constructors. Nothing to sync.")
        return False

    inserted = 0
    updated = 0

    try:
        for entry in constructor_standings:
            c = entry["Constructor"]
            jolpica_ref = c["constructorId"]
            name = c["name"]

            team = db.query(Team).filter(Team.jolpica_ref == jolpica_ref).first()

            if team:
                team.name = name
                team.constructor_name = name
                updated += 1
            else:
                db.add(Team(
                    jolpica_ref=jolpica_ref,
                    name=name,
                    constructor_name=name,
                    base=None,
                ))
                inserted += 1

        db.commit()
        print(f"  OK — {inserted} inserted, {updated} updated.")
        return True

    except Exception as e:
        db.rollback()
        print(f"  ERROR saving teams to database: {e}")
        return False


def sync_drivers(db: Session) -> bool:
    print("\n[Drivers]")

    try:
        driver_standings = fetch_driver_standings()
    except RuntimeError as e:
        print(f"  ERROR fetching drivers from Jolpica: {e}")
        return False

    if not driver_standings:
        print("  WARNING: Jolpica returned 0 drivers. Nothing to sync.")
        return False

    inserted = 0
    updated = 0
    skipped = 0

    try:
        for entry in driver_standings:
            d = entry["Driver"]
            jolpica_ref = d["driverId"]
            code = d.get("code", "")
            full_name = f"{d['givenName']} {d['familyName']}"
            nationality = d.get("nationality")
            number_str = d.get("permanentNumber")
            driver_number = int(number_str) if number_str else None

            team = None
            constructors = entry.get("Constructors", [])
            if constructors:
                team = db.query(Team).filter(
                    Team.jolpica_ref == constructors[0]["constructorId"]
                ).first()
                if not team:
                    print(f"  WARNING: team '{constructors[0]['constructorId']}' not found for {full_name}. Driver will have no team.")

            driver = db.query(Driver).filter(Driver.jolpica_ref == jolpica_ref).first()

            if driver:
                driver.code = code
                driver.full_name = full_name
                driver.nationality = nationality
                driver.driver_number = driver_number
                driver.team_id = team.id if team else driver.team_id
                updated += 1
            else:
                db.add(Driver(
                    jolpica_ref=jolpica_ref,
                    code=code,
                    full_name=full_name,
                    nationality=nationality,
                    driver_number=driver_number,
                    team_id=team.id if team else None,
                ))
                inserted += 1

        db.commit()
        print(f"  OK — {inserted} inserted, {updated} updated, {skipped} skipped.")
        return True

    except Exception as e:
        db.rollback()
        print(f"  ERROR saving drivers to database: {e}")
        return False


def sync_race_calendar(db: Session) -> bool:
    print("\n[Race Calendar]")

    try:
        races = fetch_race_calendar()
    except RuntimeError as e:
        print(f"  ERROR fetching race calendar from Jolpica: {e}")
        return False

    if not races:
        print("  WARNING: Jolpica returned 0 races. Nothing to sync.")
        return False

    inserted = 0
    updated = 0

    try:
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
                updated += 1
            else:
                db.add(Race(
                    season=season,
                    round=round_num,
                    name=name,
                    circuit_name=circuit_name,
                    country=country,
                    start_date=start_date,
                ))
                inserted += 1

        db.commit()
        print(f"  OK — {inserted} inserted, {updated} updated.")
        return True

    except Exception as e:
        db.rollback()
        print(f"  ERROR saving races to database: {e}")
        return False


def sync_driver_standings(db: Session) -> bool:
    print("\n[Driver Standings]")

    try:
        driver_standings = fetch_driver_standings()
    except RuntimeError as e:
        print(f"  ERROR fetching driver standings from Jolpica: {e}")
        return False

    if not driver_standings:
        print("  WARNING: Jolpica returned 0 standings. Nothing to sync.")
        return False

    inserted = 0
    updated = 0
    skipped = 0

    try:
        for entry in driver_standings:
            jolpica_ref = entry["Driver"]["driverId"]
            position = int(entry["position"])
            points = float(entry["points"])
            wins = int(entry["wins"])

            driver = db.query(Driver).filter(Driver.jolpica_ref == jolpica_ref).first()
            if not driver:
                print(f"  WARNING: driver '{jolpica_ref}' not in DB — skipping standing.")
                skipped += 1
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
                updated += 1
            else:
                db.add(DriverStanding(
                    season=SEASON,
                    driver_id=driver.id,
                    team_id=team.id if team else None,
                    position=position,
                    points=points,
                    wins=wins,
                    podiums=0,
                ))
                inserted += 1

        db.commit()
        print(f"  OK — {inserted} inserted, {updated} updated, {skipped} skipped.")
        return True

    except Exception as e:
        db.rollback()
        print(f"  ERROR saving driver standings to database: {e}")
        return False


def sync_all(db: Session) -> None:
    print(f"=== GridPulse F1 Data Sync — {SEASON} season ===")

    results = {
        "Teams":            sync_teams(db),
        "Drivers":          sync_drivers(db),
        "Race Calendar":    sync_race_calendar(db),
        "Driver Standings": sync_driver_standings(db),
    }

    print("\n=== Sync Summary ===")
    all_ok = True
    for step, success in results.items():
        status = "OK" if success else "FAILED"
        print(f"  {step:<20} {status}")
        if not success:
            all_ok = False

    if all_ok:
        print("\nAll steps completed successfully.")
    else:
        print("\nSome steps failed. Check the output above for details.")
