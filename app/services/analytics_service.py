"""
analytics_service.py

Builds advanced analytics summaries for one session from stored GridPulse data.
Analytics are derived from laps, stints, race control messages, and weather samples.

Used by:
  - GET /sessions/{id}/analytics  (Phase 14 endpoint)
  - The AI context builder (via format_analytics_context_lines)

Design rules:
  - Summarise everything — never return raw row dumps.
  - Handle missing data gracefully — every section has a has_X flag.
  - No ML, no predictions, no live timing.
  - All lap time averages exclude pit-out laps and null durations.
  - Averages require at least _MIN_LAPS_FOR_AVERAGE valid laps to be reported.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.orm import Session as DBSession

from app.models.driver import Driver
from app.models.favorite_driver import FavoriteDriver
from app.models.lap import Lap
from app.models.race_control_message import RaceControlMessage
from app.models.session import Session as RaceSession
from app.models.stint import Stint
from app.models.team import Team
from app.models.user import User
from app.models.weather_sample import WeatherSample

# Minimum timed laps required before we report an average.
# Fewer than this means the sample is too small to be meaningful
# (e.g. a driver who retired on lap 2).
_MIN_LAPS_FOR_AVERAGE = 3

# RC flag/keyword patterns that mark a lap as affected by a full-course event.
# Laps during these events have artificially slow times and skew averages.
_PACE_AFFECTING_FLAGS = {"SAFETY CAR", "SC", "VSC", "RED"}
_PACE_AFFECTING_KEYWORDS = ["SAFETY CAR", "VIRTUAL SAFETY CAR", "RED FLAG"]


# ─── Public data structures (smallest → largest) ──────────────────────────────

@dataclass
class DriverPaceSummary:
    """Lap pace data for one driver in a session."""
    driver_number: int
    driver_name: str
    lap_count: int               # total lap rows stored for this driver
    timed_lap_count: int         # laps with a valid lap_duration (pit-out excluded)
    fastest_lap: float | None    # seconds; None if no timed laps
    average_lap: float | None    # seconds; None if fewer than _MIN_LAPS_FOR_AVERAGE
    best_s1: float | None        # best sector-1 time across all laps
    best_s2: float | None
    best_s3: float | None
    is_favourite: bool


@dataclass
class CompoundPaceSummary:
    """
    Average lap pace on one tyre compound, derived by joining laps to
    their stint's lap range. Only stints with valid lap_start and lap_end
    contribute — stints missing those fields are counted in the data note.
    """
    compound: str
    avg_lap_time: float | None   # seconds; None if no valid laps found
    fastest_lap_time: float | None
    driver_count: int
    sample_lap_count: int        # how many laps contributed to the average


@dataclass
class StintPaceEntry:
    """Average pace for one driver on one specific stint."""
    driver_number: int
    driver_name: str
    stint_number: int | None
    compound: str | None
    lap_start: int | None
    lap_end: int | None
    avg_lap_time: float | None   # seconds; None if fewer than _MIN_LAPS_FOR_AVERAGE
    laps_counted: int            # valid timed laps in this stint
    is_favourite: bool


@dataclass
class TeammateComparison:
    """
    Pace delta between two teammates for a session.

    fastest_delta and avg_delta are (driver_a - driver_b) in seconds.
    A negative value means driver A is faster.
    None when either driver lacks enough data.
    """
    team_name: str
    driver_a_number: int
    driver_a_name: str
    driver_a_fastest: float | None
    driver_a_avg: float | None
    driver_b_number: int
    driver_b_name: str
    driver_b_fastest: float | None
    driver_b_avg: float | None
    fastest_delta: float | None
    avg_delta: float | None


@dataclass
class DriverComparison:
    """
    Side-by-side analytics for two specific drivers within a session.
    Extracted from the pre-built driver_pace list by compare_drivers().
    """
    driver_a: DriverPaceSummary
    driver_b: DriverPaceSummary
    fastest_delta: float | None   # driver_a.fastest_lap - driver_b.fastest_lap
    avg_delta: float | None       # driver_a.average_lap - driver_b.average_lap
    driver_a_stints: list[StintPaceEntry] = field(default_factory=list)
    driver_b_stints: list[StintPaceEntry] = field(default_factory=list)


@dataclass
class LatestWeather:
    """The most recent weather reading for the session."""
    air_temperature: float | None
    track_temperature: float | None
    humidity: float | None
    rainfall: bool | None
    wind_speed: float | None


@dataclass
class SessionAnalyticsSummary:
    """
    Complete analytics payload for one session.

    has_* flags signal which sections have data — callers should check these
    before rendering so they can display appropriate empty states.
    has_compound_pace is separate from has_stint_data because compound pace
    additionally requires stints to have valid lap_start / lap_end values.
    """
    # ── Identity ──────────────────────────────────────────────────────────────
    session_id: int
    session_name: str
    session_type: str
    race_name: str
    circuit_short_name: str | None
    country_name: str | None
    start_time: datetime | None
    is_synced: bool

    # ── Availability flags ────────────────────────────────────────────────────
    has_lap_data: bool
    has_stint_data: bool
    has_rc_data: bool
    has_weather_data: bool
    has_compound_pace: bool   # True only when laps can be joined to stint ranges

    # ── Session-level pace ────────────────────────────────────────────────────
    session_fastest_lap: float | None    # best single lap across all drivers
    session_fastest_driver: str | None   # name of that driver
    session_avg_lap: float | None        # mean of all timed laps in the session

    # ── Per-driver pace ───────────────────────────────────────────────────────
    driver_pace: list[DriverPaceSummary]   # sorted: fastest first; None times last

    # ── Compound pace (requires lap ↔ stint join) ─────────────────────────────
    compound_pace: list[CompoundPaceSummary]   # sorted: fastest average first

    # ── Per-stint pace breakdown ──────────────────────────────────────────────
    stint_pace: list[StintPaceEntry]   # all drivers, all stints with lap ranges

    # ── Teammate comparisons (one entry per team with 2 drivers in session) ───
    teammate_comparisons: list[TeammateComparison]

    # ── Race context (safety car / red flag lap numbers for pace context) ─────
    rc_total: int
    safety_car_laps: list[int]
    red_flag_laps: list[int]
    latest_weather: LatestWeather | None

    # ── Data quality note ─────────────────────────────────────────────────────
    # Plain-English note when data completeness limits certain calculations.
    # None when data is complete.
    data_note: str | None

    # ── Personalisation ───────────────────────────────────────────────────────
    favourite_driver_numbers: set[int] = field(default_factory=set)


# ─── Private helpers ──────────────────────────────────────────────────────────

def _driver_name_map(db: DBSession) -> dict[int, str]:
    """Map driver_number → full_name for all known drivers."""
    return {
        d.driver_number: d.full_name
        for d in db.query(Driver).all()
        if d.driver_number is not None
    }


def _favourite_numbers(user: User | None, db: DBSession) -> set[int]:
    """Return the set of favourite driver numbers for the given user, or empty."""
    if user is None:
        return set()
    favs = (
        db.query(FavoriteDriver)
        .filter(FavoriteDriver.user_id == user.id)
        .all()
    )
    return {
        fd.driver.driver_number
        for fd in favs
        if fd.driver and fd.driver.driver_number is not None
    }


def _r3(v: float | None) -> float | None:
    """Round to 3 decimal places (millisecond precision). None-safe."""
    return round(v, 3) if v is not None else None


def _build_driver_pace(
    laps: list[Lap],
    names: dict[int, str],
    favs: set[int],
) -> list[DriverPaceSummary]:
    """
    Build a per-driver pace summary from raw lap rows.

    Pit-out laps and laps with no recorded lap_duration are excluded from
    fastest and average calculations. Sector bests are the minimum recorded
    sector time across all of a driver's laps (not just timed laps — sectors
    can be valid even when the overall lap time is not).
    """
    by_driver: dict[int, list[Lap]] = defaultdict(list)
    for lap in laps:
        by_driver[lap.driver_number].append(lap)

    summaries: list[DriverPaceSummary] = []
    for dn, driver_laps in by_driver.items():
        timed = [
            lap.lap_duration
            for lap in driver_laps
            if not lap.is_pit_out_lap and lap.lap_duration is not None
        ]
        s1_vals = [lap.duration_sector_1 for lap in driver_laps if lap.duration_sector_1 is not None]
        s2_vals = [lap.duration_sector_2 for lap in driver_laps if lap.duration_sector_2 is not None]
        s3_vals = [lap.duration_sector_3 for lap in driver_laps if lap.duration_sector_3 is not None]

        avg = _r3(sum(timed) / len(timed)) if len(timed) >= _MIN_LAPS_FOR_AVERAGE else None

        summaries.append(DriverPaceSummary(
            driver_number=dn,
            driver_name=names.get(dn, f"Driver #{dn}"),
            lap_count=len(driver_laps),
            timed_lap_count=len(timed),
            fastest_lap=_r3(min(timed)) if timed else None,
            average_lap=avg,
            best_s1=_r3(min(s1_vals)) if s1_vals else None,
            best_s2=_r3(min(s2_vals)) if s2_vals else None,
            best_s3=_r3(min(s3_vals)) if s3_vals else None,
            is_favourite=dn in favs,
        ))

    # Sort: fastest lap ascending; drivers with no timed laps go to the end.
    return sorted(summaries, key=lambda d: (d.fastest_lap is None, d.fastest_lap or 0))


def _build_compound_pace(
    laps: list[Lap],
    stints: list[Stint],
) -> tuple[list[CompoundPaceSummary], bool]:
    """
    Build per-compound pace by joining laps to their stint's lap range.

    Returns (compound_pace_list, has_compound_pace).
    has_compound_pace is False when no stints have valid lap ranges, making
    the join impossible.
    """
    # Only use stints that have valid lap ranges for the join.
    ranged_stints = [s for s in stints if s.compound and s.lap_start is not None and s.lap_end is not None]

    if not ranged_stints:
        return [], False

    # Build a lookup: driver_number → list of stints with lap ranges.
    stint_map: dict[int, list[Stint]] = defaultdict(list)
    for s in ranged_stints:
        stint_map[s.driver_number].append(s)

    # For each timed lap, find which compound it was on.
    compound_times: dict[str, list[float]] = defaultdict(list)
    compound_drivers: dict[str, set[int]] = defaultdict(set)

    for lap in laps:
        if lap.is_pit_out_lap or lap.lap_duration is None:
            continue
        for s in stint_map.get(lap.driver_number, []):
            if s.lap_start <= lap.lap_number <= s.lap_end:
                compound_times[s.compound].append(lap.lap_duration)
                compound_drivers[s.compound].add(lap.driver_number)
                break  # a lap belongs to at most one stint

    if not compound_times:
        return [], False

    results: list[CompoundPaceSummary] = []
    for compound, times in compound_times.items():
        results.append(CompoundPaceSummary(
            compound=compound,
            avg_lap_time=_r3(sum(times) / len(times)) if times else None,
            fastest_lap_time=_r3(min(times)) if times else None,
            driver_count=len(compound_drivers[compound]),
            sample_lap_count=len(times),
        ))

    # Sort by average lap time ascending; None values go last.
    results.sort(key=lambda c: (c.avg_lap_time is None, c.avg_lap_time or 0))
    return results, True


def _build_stint_pace(
    laps: list[Lap],
    stints: list[Stint],
    names: dict[int, str],
    favs: set[int],
) -> list[StintPaceEntry]:
    """
    Build per-driver per-stint pace entries by collecting laps within each
    stint's lap range and averaging their durations.

    Only stints with valid lap_start / lap_end are included.
    Stints with fewer than _MIN_LAPS_FOR_AVERAGE timed laps still appear
    in the list but show avg_lap_time = None.
    """
    # Build a lookup: driver_number → list of that driver's laps.
    lap_map: dict[int, list[Lap]] = defaultdict(list)
    for lap in laps:
        lap_map[lap.driver_number].append(lap)

    entries: list[StintPaceEntry] = []
    for s in stints:
        if s.lap_start is None or s.lap_end is None:
            continue  # cannot assign laps without a range

        driver_laps = lap_map.get(s.driver_number, [])
        stint_laps = [
            lap.lap_duration
            for lap in driver_laps
            if s.lap_start <= lap.lap_number <= s.lap_end
            and not lap.is_pit_out_lap
            and lap.lap_duration is not None
        ]

        avg = _r3(sum(stint_laps) / len(stint_laps)) if len(stint_laps) >= _MIN_LAPS_FOR_AVERAGE else None

        entries.append(StintPaceEntry(
            driver_number=s.driver_number,
            driver_name=names.get(s.driver_number, f"Driver #{s.driver_number}"),
            stint_number=s.stint_number,
            compound=s.compound,
            lap_start=s.lap_start,
            lap_end=s.lap_end,
            avg_lap_time=avg,
            laps_counted=len(stint_laps),
            is_favourite=s.driver_number in favs,
        ))

    # Sort by driver number, then stint number.
    entries.sort(key=lambda e: (e.driver_number, e.stint_number or 0))
    return entries


def _build_teammate_comparisons(
    driver_pace: list[DriverPaceSummary],
    driver_numbers_in_session: set[int],
    db: DBSession,
) -> list[TeammateComparison]:
    """
    Build one TeammateComparison per team that has exactly two drivers
    present in this session.

    Queries the drivers and teams tables to find which two drivers share
    a team, then pairs their DriverPaceSummary entries.
    """
    # Query drivers who appear in this session, joining to their team.
    drivers_with_teams = (
        db.query(Driver)
        .filter(Driver.driver_number.in_(driver_numbers_in_session))
        .filter(Driver.team_id.isnot(None))
        .all()
    )

    # Group driver numbers by team_id.
    by_team: dict[int, list[Driver]] = defaultdict(list)
    for d in drivers_with_teams:
        by_team[d.team_id].append(d)

    # Build a lookup from driver_number to DriverPaceSummary.
    pace_map: dict[int, DriverPaceSummary] = {
        dp.driver_number: dp for dp in driver_pace
    }

    comparisons: list[TeammateComparison] = []
    for team_id, team_drivers in by_team.items():
        if len(team_drivers) != 2:
            continue  # skip teams with only 1 driver present (retired, etc.)

        da_model, db_model = sorted(team_drivers, key=lambda d: d.driver_number or 0)
        pa = pace_map.get(da_model.driver_number)
        pb = pace_map.get(db_model.driver_number)

        if pa is None or pb is None:
            continue

        team = da_model.team
        team_name = team.name if team else f"Team {team_id}"

        fastest_delta = (
            _r3(pa.fastest_lap - pb.fastest_lap)
            if pa.fastest_lap is not None and pb.fastest_lap is not None
            else None
        )
        avg_delta = (
            _r3(pa.average_lap - pb.average_lap)
            if pa.average_lap is not None and pb.average_lap is not None
            else None
        )

        comparisons.append(TeammateComparison(
            team_name=team_name,
            driver_a_number=pa.driver_number,
            driver_a_name=pa.driver_name,
            driver_a_fastest=pa.fastest_lap,
            driver_a_avg=pa.average_lap,
            driver_b_number=pb.driver_number,
            driver_b_name=pb.driver_name,
            driver_b_fastest=pb.fastest_lap,
            driver_b_avg=pb.average_lap,
            fastest_delta=fastest_delta,
            avg_delta=avg_delta,
        ))

    # Sort by absolute fastest delta (tightest battle first).
    comparisons.sort(key=lambda c: (c.fastest_delta is None, abs(c.fastest_delta or 0)))
    return comparisons


def _extract_rc_context(
    rc_messages: list[RaceControlMessage],
) -> tuple[list[int], list[int]]:
    """
    Return two sorted lists of lap numbers: safety car deployments and red flags.
    These help the AI flag that lap times on those laps are not representative
    of true race pace.
    """
    safety_car_laps: set[int] = set()
    red_flag_laps: set[int] = set()

    for msg in rc_messages:
        if msg.lap_number is None:
            continue
        flag = (msg.flag or "").upper()
        text = (msg.message or "").upper()

        if flag in ("SC", "SAFETY CAR") or "SAFETY CAR DEPLOYED" in text:
            safety_car_laps.add(msg.lap_number)
        elif flag == "RED" or "RED FLAG" in text:
            red_flag_laps.add(msg.lap_number)

    return sorted(safety_car_laps), sorted(red_flag_laps)


def _latest_weather(samples: list[WeatherSample]) -> LatestWeather | None:
    """Return the most recent weather reading, or None if no samples exist."""
    if not samples:
        return None
    dated = [s for s in samples if s.date is not None]
    latest = max(dated, key=lambda s: s.date) if dated else samples[-1]
    return LatestWeather(
        air_temperature=latest.air_temperature,
        track_temperature=latest.track_temperature,
        humidity=latest.humidity,
        rainfall=latest.rainfall,
        wind_speed=latest.wind_speed,
    )


def _build_data_note(
    stints: list[Stint],
    has_lap_data: bool,
    has_stint_data: bool,
) -> str | None:
    """
    Produce a plain-English note when data gaps limit certain calculations.
    Returns None when data is complete.
    """
    if not has_lap_data:
        return "No lap data is synced for this session — pace analytics are unavailable."

    if not has_stint_data:
        return "No stint data is synced — compound pace breakdown is unavailable."

    # Check what fraction of stints are missing lap ranges.
    if stints:
        missing_ranges = sum(
            1 for s in stints
            if s.compound and (s.lap_start is None or s.lap_end is None)
        )
        if missing_ranges > 0:
            pct = round(100 * missing_ranges / len(stints))
            return (
                f"{missing_ranges} of {len(stints)} stints ({pct}%) are missing lap ranges — "
                f"compound pace data may be partial."
            )

    return None


# ─── Public API ───────────────────────────────────────────────────────────────

def build_session_analytics(
    session: RaceSession,
    db: DBSession,
    current_user: User | None = None,
) -> SessionAnalyticsSummary:
    """
    Build a complete analytics summary for one session.

    Pass current_user to enable favourite-driver highlighting; pass None
    for unauthenticated callers (is_favourite fields default to False).

    All calculations use stored data only — no ML, no predictions.
    """
    names = _driver_name_map(db)
    favs = _favourite_numbers(current_user, db)
    race_name = session.race.name if session.race else f"Race {session.race_id}"

    # ── Laps ──────────────────────────────────────────────────────────────────
    laps = (
        db.query(Lap)
        .filter(Lap.session_id == session.id)
        .order_by(Lap.driver_number, Lap.lap_number)
        .all()
    )
    has_lap_data = len(laps) > 0

    # ── Stints ────────────────────────────────────────────────────────────────
    stints = (
        db.query(Stint)
        .filter(Stint.session_id == session.id)
        .order_by(Stint.driver_number, Stint.stint_number)
        .all()
    )
    has_stint_data = len(stints) > 0

    # ── Race control ──────────────────────────────────────────────────────────
    rc_messages = (
        db.query(RaceControlMessage)
        .filter(RaceControlMessage.session_id == session.id)
        .order_by(RaceControlMessage.date)
        .all()
    )
    has_rc_data = len(rc_messages) > 0

    # ── Weather ───────────────────────────────────────────────────────────────
    weather_samples = (
        db.query(WeatherSample)
        .filter(WeatherSample.session_id == session.id)
        .all()
    )
    has_weather_data = len(weather_samples) > 0

    # ── Per-driver pace ───────────────────────────────────────────────────────
    driver_pace: list[DriverPaceSummary] = []
    if has_lap_data:
        driver_pace = _build_driver_pace(laps, names, favs)

    # ── Session-level pace stats ──────────────────────────────────────────────
    session_fastest_lap: float | None = None
    session_fastest_driver: str | None = None
    session_avg_lap: float | None = None

    if driver_pace:
        # Best single lap across all drivers (first entry is already the fastest).
        fastest = driver_pace[0]
        if fastest.fastest_lap is not None:
            session_fastest_lap = fastest.fastest_lap
            session_fastest_driver = fastest.driver_name

        # Mean of all timed laps in the session.
        all_timed = [
            lap.lap_duration
            for lap in laps
            if not lap.is_pit_out_lap and lap.lap_duration is not None
        ]
        if len(all_timed) >= _MIN_LAPS_FOR_AVERAGE:
            session_avg_lap = _r3(sum(all_timed) / len(all_timed))

    # ── Compound pace ─────────────────────────────────────────────────────────
    compound_pace: list[CompoundPaceSummary] = []
    has_compound_pace = False
    if has_lap_data and has_stint_data:
        compound_pace, has_compound_pace = _build_compound_pace(laps, stints)

    # ── Stint pace breakdown ──────────────────────────────────────────────────
    stint_pace: list[StintPaceEntry] = []
    if has_lap_data and has_stint_data:
        stint_pace = _build_stint_pace(laps, stints, names, favs)

    # ── Teammate comparisons ──────────────────────────────────────────────────
    teammate_comparisons: list[TeammateComparison] = []
    if driver_pace:
        driver_numbers_in_session = {dp.driver_number for dp in driver_pace}
        teammate_comparisons = _build_teammate_comparisons(
            driver_pace, driver_numbers_in_session, db
        )

    # ── Race context ──────────────────────────────────────────────────────────
    safety_car_laps, red_flag_laps = [], []
    if has_rc_data:
        safety_car_laps, red_flag_laps = _extract_rc_context(rc_messages)

    weather_snapshot = _latest_weather(weather_samples)

    return SessionAnalyticsSummary(
        session_id=session.id,
        session_name=session.session_name,
        session_type=session.session_type,
        race_name=race_name,
        circuit_short_name=session.circuit_short_name,
        country_name=session.country_name,
        start_time=session.start_time,
        is_synced=session.openf1_session_key is not None,
        has_lap_data=has_lap_data,
        has_stint_data=has_stint_data,
        has_rc_data=has_rc_data,
        has_weather_data=has_weather_data,
        has_compound_pace=has_compound_pace,
        session_fastest_lap=session_fastest_lap,
        session_fastest_driver=session_fastest_driver,
        session_avg_lap=session_avg_lap,
        driver_pace=driver_pace,
        compound_pace=compound_pace,
        stint_pace=stint_pace,
        teammate_comparisons=teammate_comparisons,
        rc_total=len(rc_messages),
        safety_car_laps=safety_car_laps,
        red_flag_laps=red_flag_laps,
        latest_weather=weather_snapshot,
        data_note=_build_data_note(stints, has_lap_data, has_stint_data),
        favourite_driver_numbers=favs,
    )


def get_session_analytics(
    session_id: int,
    db: DBSession,
    current_user: User | None = None,
) -> SessionAnalyticsSummary | None:
    """
    Convenience wrapper for API endpoints.
    Returns None if the session does not exist.
    """
    session = db.query(RaceSession).filter(RaceSession.id == session_id).first()
    if session is None:
        return None
    return build_session_analytics(session, db, current_user)


def compare_drivers(
    summary: SessionAnalyticsSummary,
    driver_number_a: int,
    driver_number_b: int,
) -> DriverComparison | None:
    """
    Extract a side-by-side comparison of two specific drivers from a pre-built
    SessionAnalyticsSummary. Returns None if either driver is not in the summary.

    This does not re-query the database — it reads from the already-computed
    driver_pace and stint_pace lists.
    """
    pace_map = {dp.driver_number: dp for dp in summary.driver_pace}
    pa = pace_map.get(driver_number_a)
    pb = pace_map.get(driver_number_b)

    if pa is None or pb is None:
        return None

    fastest_delta = (
        _r3(pa.fastest_lap - pb.fastest_lap)
        if pa.fastest_lap is not None and pb.fastest_lap is not None
        else None
    )
    avg_delta = (
        _r3(pa.average_lap - pb.average_lap)
        if pa.average_lap is not None and pb.average_lap is not None
        else None
    )

    a_stints = [e for e in summary.stint_pace if e.driver_number == driver_number_a]
    b_stints = [e for e in summary.stint_pace if e.driver_number == driver_number_b]

    return DriverComparison(
        driver_a=pa,
        driver_b=pb,
        fastest_delta=fastest_delta,
        avg_delta=avg_delta,
        driver_a_stints=a_stints,
        driver_b_stints=b_stints,
    )


def format_analytics_context_lines(summary: SessionAnalyticsSummary) -> list[str]:
    """
    Produce compact context lines for the AI context builder.

    Covers: session fastest lap, top-5 drivers by pace, compound averages,
    and safety car / red flag laps (which explain slow lap clusters).
    RC events and weather are handled by the existing session_block — no
    duplication here.

    Designed to be imported by ai_context.py without coupling it to the
    internal helpers in this module.
    """
    if not summary.has_lap_data:
        return [f"[{summary.session_name}] Missing: no_lap_data — pace analytics unavailable."]

    lines: list[str] = [
        f"[{summary.session_name} — {summary.race_name}] Pace analytics:"
    ]

    # Session fastest lap
    if summary.session_fastest_lap is not None:
        lines.append(
            f"  Fastest lap : {summary.session_fastest_lap}s "
            f"({summary.session_fastest_driver})"
        )
    if summary.session_avg_lap is not None:
        lines.append(f"  Session avg : {summary.session_avg_lap}s (all timed laps)")

    # Top-5 drivers by fastest lap
    top5 = [dp for dp in summary.driver_pace if dp.fastest_lap is not None][:5]
    if top5:
        lines.append("  Driver pace (top 5 by fastest lap):")
        for dp in top5:
            avg_str = f", avg {dp.average_lap}s" if dp.average_lap is not None else ""
            lines.append(
                f"    {dp.driver_name} (#{dp.driver_number}): "
                f"fastest {dp.fastest_lap}s{avg_str}"
            )

    # Compound pace
    if summary.has_compound_pace and summary.compound_pace:
        parts = []
        for cp in summary.compound_pace:
            if cp.avg_lap_time is not None:
                parts.append(f"{cp.compound} avg {cp.avg_lap_time}s ({cp.sample_lap_count} laps)")
        if parts:
            lines.append("  Compound avg pace: " + "; ".join(parts))

    # Safety car / red flag laps (pace context)
    if summary.safety_car_laps:
        laps_str = ", ".join(str(l) for l in summary.safety_car_laps[:5])
        lines.append(f"  Safety car laps: {laps_str} — lap times on these laps are not race pace.")
    if summary.red_flag_laps:
        laps_str = ", ".join(str(l) for l in summary.red_flag_laps[:3])
        lines.append(f"  Red flag laps: {laps_str} — laps after restart are out-laps.")

    if summary.data_note:
        lines.append(f"  Note: {summary.data_note}")

    return lines
