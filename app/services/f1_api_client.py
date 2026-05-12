import requests

BASE_URL = "https://api.jolpi.ca/ergast/f1"
SEASON = 2025


def _get(url: str) -> dict:
    print(f"  Fetching: {url}")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Could not connect to Jolpica API. Check your internet connection.")
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Request timed out after 10 seconds: {url}")
    except requests.exceptions.HTTPError as e:
        raise RuntimeError(f"Jolpica returned HTTP error {response.status_code}: {e}")


def fetch_race_calendar(season: int = SEASON) -> list[dict]:
    url = f"{BASE_URL}/{season}/races.json?limit=100"
    data = _get(url)
    return data["MRData"]["RaceTable"]["Races"]


def fetch_driver_standings(season: int = SEASON) -> list[dict]:
    url = f"{BASE_URL}/{season}/driverStandings.json"
    data = _get(url)
    standings_lists = data["MRData"]["StandingsTable"]["StandingsLists"]
    if not standings_lists:
        return []
    return standings_lists[0]["DriverStandings"]


def fetch_constructor_standings(season: int = SEASON) -> list[dict]:
    url = f"{BASE_URL}/{season}/constructorStandings.json"
    data = _get(url)
    standings_lists = data["MRData"]["StandingsTable"]["StandingsLists"]
    if not standings_lists:
        return []
    return standings_lists[0]["ConstructorStandings"]
