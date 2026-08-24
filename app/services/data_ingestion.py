from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.models.driver import Driver
from app.models.race import Race
from app.models.race_result import RaceResult
from app.models.session import Session as RaceSession
from app.models.standing import DriverStanding
from app.models.team import Team
from app.services.f1_api_client import (
    SEASON,
    fetch_constructor_standings,
    fetch_driver_standings,
    fetch_race_calendar,
    fetch_race_results,
)

# Maps Jolpica race dict keys to (session_type, session_name).
# Order matters: Sprint must come before Qualifying so the sprint weekend
# session set is recognised correctly.
_SESSION_KEY_MAP = [
    ("FirstPractice",    "fp1",               "Practice 1"),
    ("SecondPractice",   "fp2",               "Practice 2"),
    ("ThirdPractice",    "fp3",               "Practice 3"),
    ("SprintShootout",   "sprint_qualifying", "Sprint Qualifying"),
    ("SprintQualifying", "sprint_qualifying", "Sprint Qualifying"),
    ("Sprint",           "sprint",            "Sprint"),
    ("Qualifying",       "qualifying",        "Qualifying"),
]


def _parse_session_time(date_str: str | None, time_str: str | None) -> datetime | None:
    if not date_str:
        return None
    if time_str:
        iso = f"{date_str}T{time_str.replace('Z', '+00:00')}"
        return datetime.fromisoformat(iso)
    # Date only — store midnight UTC so the value is still useful for ordering.
    d = date.fromisoformat(date_str)
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc)


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


def sync_sessions(db: Session) -> bool:
    print("\n[Sessions]")

    try:
        races = fetch_race_calendar()
    except RuntimeError as e:
        print(f"  ERROR fetching race calendar for sessions: {e}")
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

            race = db.query(Race).filter(
                Race.season == season,
                Race.round == round_num,
            ).first()

            if not race:
                print(f"  WARNING: Race not found for season={season} round={round_num}. Run calendar sync first.")
                continue

            # Build the list of (session_type, session_name, start_time) for this race.
            sessions_to_sync: list[tuple[str, str, datetime | None]] = []

            for jolpica_key, session_type, session_name in _SESSION_KEY_MAP:
                sub = race_data.get(jolpica_key)
                if sub:
                    start_time = _parse_session_time(sub.get("date"), sub.get("time"))
                    sessions_to_sync.append((session_type, session_name, start_time))

            # Race session — top-level date/time fields.
            race_start = _parse_session_time(race_data.get("date"), race_data.get("time"))
            sessions_to_sync.append(("race", "Race", race_start))

            for session_type, session_name, start_time in sessions_to_sync:
                existing = db.query(RaceSession).filter_by(
                    race_id=race.id,
                    session_type=session_type,
                ).first()

                if existing:
                    existing.session_name = session_name
                    existing.start_time = start_time
                    updated += 1
                else:
                    db.add(RaceSession(
                        race_id=race.id,
                        session_type=session_type,
                        session_name=session_name,
                        start_time=start_time,
                        end_time=None,
                        timezone=None,
                    ))
                    inserted += 1

        db.commit()
        print(f"  OK — {inserted} inserted, {updated} updated.")
        return True

    except Exception as e:
        db.rollback()
        print(f"  ERROR saving sessions to database: {e}")
        return False


def sync_race_results(db: Session) -> bool:
    """
    Sync the official classified result (position, status, points) for every
    round of the season that has already happened. Rounds that haven't run yet
    return an empty result list from Jolpica and are skipped, not an error.
    """
    print("\n[Race Results]")

    races = db.query(Race).filter(Race.season == SEASON).order_by(Race.round).all()
    if not races:
        print("  WARNING: No races in DB for this season. Run calendar sync first.")
        return False

    inserted = 0
    updated = 0
    not_yet_run = 0

    try:
        for race in races:
            try:
                results = fetch_race_results(SEASON, race.round)
            except RuntimeError as e:
                print(f"  ERROR fetching results for round {race.round}: {e}")
                continue

            if not results:
                not_yet_run += 1
                continue

            race_session = db.query(RaceSession).filter_by(
                race_id=race.id,
                session_type="race",
            ).first()
            if not race_session:
                print(f"  WARNING: no 'race' session for round {race.round}. Run session sync first.")
                continue

            for r in results:
                jolpica_ref = r["Driver"]["driverId"]
                driver = db.query(Driver).filter(Driver.jolpica_ref == jolpica_ref).first()
                if not driver:
                    print(f"  WARNING: driver '{jolpica_ref}' not in DB — skipping result row.")
                    continue

                team = None
                constructor = r.get("Constructor")
                if constructor:
                    team = db.query(Team).filter(
                        Team.jolpica_ref == constructor["constructorId"]
                    ).first()

                position = int(r["position"]) if r.get("position") else None
                points = float(r["points"]) if r.get("points") is not None else None
                laps = int(r["laps"]) if r.get("laps") is not None else None
                grid = int(r["grid"]) if r.get("grid") is not None else None
                finish_time = r.get("Time", {}).get("time")

                existing = db.query(RaceResult).filter_by(
                    session_id=race_session.id,
                    driver_id=driver.id,
                ).first()

                if existing:
                    existing.position = position
                    existing.position_text = r.get("positionText")
                    existing.status = r.get("status")
                    existing.grid = grid
                    existing.points = points
                    existing.laps = laps
                    existing.finish_time = finish_time
                    existing.team_id = team.id if team else existing.team_id
                    updated += 1
                else:
                    db.add(RaceResult(
                        session_id=race_session.id,
                        driver_id=driver.id,
                        team_id=team.id if team else None,
                        position=position,
                        position_text=r.get("positionText"),
                        status=r.get("status"),
                        grid=grid,
                        points=points,
                        laps=laps,
                        finish_time=finish_time,
                    ))
                    inserted += 1

        db.commit()
        print(f"  OK — {inserted} inserted, {updated} updated, {not_yet_run} rounds not yet run.")
        return True

    except Exception as e:
        db.rollback()
        print(f"  ERROR saving race results to database: {e}")
        return False


def sync_all(db: Session) -> None:
    print(f"=== GridPulse F1 Data Sync — {SEASON} season ===")

    # Sessions must run after Race Calendar so race rows already exist.
    # Race Results must run after Sessions so the "race"-type session exists.
    results = {
        "Teams":            sync_teams(db),
        "Drivers":          sync_drivers(db),
        "Race Calendar":    sync_race_calendar(db),
        "Sessions":         sync_sessions(db),
        "Driver Standings": sync_driver_standings(db),
        "Race Results":     sync_race_results(db),
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
