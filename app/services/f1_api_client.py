import requests

BASE_URL = "https://api.jolpi.ca/ergast/f1"
SEASON = 2025


def _get(url: str) -> dict:
    """Make a GET request and return parsed JSON. Raises on failure."""
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(f"Could not connect to Jolpica API. Check your internet connection.")
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Request timed out: {url}")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"API returned an error: {e}")


def fetch_race_calendar(season: int = SEASON) -> list[dict]:
    """Fetch the full race calendar for a given season."""
    url = f"{BASE_URL}/{season}/races.json?limit=100"
    data = _get(url)
    return data["MRData"]["RaceTable"]["Races"]


def fetch_driver_standings(season: int = SEASON) -> list[dict]:
    """Fetch the current driver championship standings for a given season."""
    url = f"{BASE_URL}/{season}/driverStandings.json"
    data = _get(url)

    standings_lists = data["MRData"]["StandingsTable"]["StandingsLists"]

    if not standings_lists:
        return []

    return standings_lists[0]["DriverStandings"]


def fetch_constructor_standings(season: int = SEASON) -> list[dict]:
    """Fetch the current constructor championship standings for a given season."""
    url = f"{BASE_URL}/{season}/constructorStandings.json"
    data = _get(url)

    standings_lists = data["MRData"]["StandingsTable"]["StandingsLists"]

    if not standings_lists:
        return []

    return standings_lists[0]["ConstructorStandings"]
