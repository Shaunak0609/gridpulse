import os
import time

import requests

BASE_URL = os.getenv("OPENF1_BASE_URL", "https://api.openf1.org/v1")

# OpenF1 is a free public API — no API key required, but it aggressively
# rate-limits bursts of requests (HTTP 429). A single session pulls from
# five endpoints back to back, so retry with backoff instead of failing
# the whole sync on the first 429.
MAX_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 2

# OpenF1 is a free public API — no API key required.
# Responses are JSON arrays. Every endpoint supports query parameters for
# filtering (e.g. ?session_key=9158&driver_number=44).


def _get(path: str, params: dict | None = None) -> list[dict]:
    """
    Make a GET request to the OpenF1 API, retrying on rate limiting (429).

    OpenF1 always returns a JSON array (even for a single result).
    Raises RuntimeError on connection failure, timeout, or non-2xx response
    that isn't resolved after retries.
    """
    url = f"{BASE_URL}{path}"
    print(f"  Fetching: {url}" + (f" params={params}" if params else ""))

    backoff = INITIAL_BACKOFF_SECONDS
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(url, params=params, timeout=30)
            if response.status_code == 429 and attempt < MAX_RETRIES:
                wait = float(response.headers.get("Retry-After", backoff))
                print(f"    Rate limited (429) — retrying in {wait:.0f}s "
                      f"(attempt {attempt}/{MAX_RETRIES})")
                time.sleep(wait)
                backoff *= 2
                continue
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            raise RuntimeError(
                "Could not connect to OpenF1 API. Check your internet connection."
            )
        except requests.exceptions.Timeout:
            raise RuntimeError(f"Request timed out after 30 seconds: {url}")
        except requests.exceptions.HTTPError:
            raise RuntimeError(
                f"OpenF1 returned HTTP {response.status_code} for {url}"
            )

    raise RuntimeError(
        f"OpenF1 returned HTTP 429 for {url} after {MAX_RETRIES} retries."
    )


# ─── Meetings ────────────────────────────────────────────────────────────────

def fetch_meetings(year: int) -> list[dict]:
    """
    Return all race weekends (meetings) for the given season.

    Each meeting includes meeting_key, meeting_name, circuit_short_name,
    country_name, date_start, gmt_offset, and location.

    Example:
        meetings = fetch_meetings(2024)
        # [{"meeting_key": 1229, "meeting_name": "Bahrain Grand Prix", ...}, ...]
    """
    return _get("/meetings", params={"year": year})


# ─── Sessions ─────────────────────────────────────────────────────────────────

def fetch_sessions(year: int) -> list[dict]:
    """
    Return all sessions for the given season across all race weekends.

    Each session includes session_key (the primary OpenF1 identifier),
    session_name, session_type, meeting_key, date_start, date_end,
    circuit_short_name, and country_name.

    session_key is used as the main filter parameter for all other endpoints.

    Example:
        sessions = fetch_sessions(2024)
        # [{"session_key": 9158, "session_name": "Race", "session_type": "Race", ...}, ...]
    """
    return _get("/sessions", params={"year": year})


def fetch_session(session_key: int) -> dict | None:
    """
    Return a single session by its session_key, or None if not found.

    Example:
        session = fetch_session(9158)
        # {"session_key": 9158, "session_name": "Race", ...}
    """
    results = _get("/sessions", params={"session_key": session_key})
    return results[0] if results else None


# ─── Drivers ──────────────────────────────────────────────────────────────────

def fetch_drivers(session_key: int) -> list[dict]:
    """
    Return the list of drivers who participated in a session.

    Each entry includes driver_number, full_name, name_acronym, team_name,
    team_colour, headshot_url, and country_code.

    Note: driver_number is the primary identifier in all OpenF1 data.
    It maps to the driver_number column in GridPulse's drivers table.

    Example:
        drivers = fetch_drivers(9158)
        # [{"driver_number": 1, "full_name": "Max Verstappen", "team_name": "Red Bull Racing", ...}, ...]
    """
    return _get("/drivers", params={"session_key": session_key})


# ─── Laps ─────────────────────────────────────────────────────────────────────

def fetch_laps(session_key: int, driver_number: int | None = None) -> list[dict]:
    """
    Return lap data for a session, optionally filtered to one driver.

    Each lap includes lap_number, lap_duration (seconds), duration_sector_1,
    duration_sector_2, duration_sector_3, is_pit_out_lap, and date_start.

    Fetching all drivers at once can return 1,000–1,500 rows for a race.
    Provide driver_number to fetch one driver at a time (recommended for
    initial testing and development).

    Example — all drivers:
        laps = fetch_laps(9158)

    Example — one driver:
        laps = fetch_laps(9158, driver_number=44)
    """
    params: dict = {"session_key": session_key}
    if driver_number is not None:
        params["driver_number"] = driver_number
    return _get("/laps", params=params)


# ─── Stints ───────────────────────────────────────────────────────────────────

def fetch_stints(session_key: int, driver_number: int | None = None) -> list[dict]:
    """
    Return stint data for a session, optionally filtered to one driver.

    Each stint includes driver_number, stint_number, lap_start, lap_end,
    compound (SOFT / MEDIUM / HARD / INTERMEDIATE / WET), and tyre_age_at_start.

    Stints are small (typically 2–4 per driver, ~40–80 rows per race total).
    It is safe to fetch all drivers at once.

    Example:
        stints = fetch_stints(9158)
        # [{"driver_number": 1, "stint_number": 1, "compound": "MEDIUM", "lap_start": 1, ...}, ...]
    """
    params: dict = {"session_key": session_key}
    if driver_number is not None:
        params["driver_number"] = driver_number
    return _get("/stints", params=params)


# ─── Pit stops ────────────────────────────────────────────────────────────────

def fetch_pit_stops(session_key: int, driver_number: int | None = None) -> list[dict]:
    """
    Return pit stop data for a session, optionally filtered to one driver.

    Each pit stop includes driver_number, lap_number, pit_duration (seconds
    in the pit lane), and date. pit_duration is the stationary time only.

    Example:
        pits = fetch_pit_stops(9158)
        # [{"driver_number": 1, "lap_number": 27, "pit_duration": 2.4, ...}, ...]
    """
    params: dict = {"session_key": session_key}
    if driver_number is not None:
        params["driver_number"] = driver_number
    return _get("/pit", params=params)


# ─── Race control messages ────────────────────────────────────────────────────

def fetch_race_control(session_key: int) -> list[dict]:
    """
    Return race control messages for a session, ordered by date.

    Each message includes date, lap_number, category, message, flag,
    scope, sector, and driver_number. Category values include:
      SafetyCar, Flag, Drs, CarEvent, Other

    Flag values include: GREEN, YELLOW, RED, SC, VSC, CHEQUERED

    Race control messages are typically 10–50 rows per session and are
    the most human-readable data in OpenF1 — useful for the AI assistant
    and race narrative features.

    Example:
        rc = fetch_race_control(9158)
        # [{"category": "SafetyCar", "message": "SAFETY CAR DEPLOYED", "lap_number": 12, ...}, ...]
    """
    return _get("/race_control", params={"session_key": session_key})


# ─── Weather ──────────────────────────────────────────────────────────────────

def fetch_weather(session_key: int) -> list[dict]:
    """
    Return weather snapshots for a session, recorded roughly every minute.

    Each snapshot includes air_temperature, track_temperature, humidity,
    pressure, rainfall (boolean), wind_direction (degrees), and wind_speed.

    Weather data is small (typically 60–120 rows per session) and is safe
    to fetch all at once.

    Example:
        weather = fetch_weather(9158)
        # [{"air_temperature": 31.4, "track_temperature": 45.1, "rainfall": False, ...}, ...]
    """
    return _get("/weather", params={"session_key": session_key})
