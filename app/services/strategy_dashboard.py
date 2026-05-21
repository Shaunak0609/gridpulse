"""
strategy_dashboard.py

Builds a structured strategy summary for one session from stored GridPulse data.
Strategy data is derived from stints, race control messages, and weather samples.

Used by:
  - GET /sessions/{id}/strategy  (planned Phase 13 endpoint)
  - The AI context builder (via format_strategy_context_lines)

Design rules:
  - Summarise everything — never return raw row dumps.
  - Handle missing data gracefully — every section has a has_X flag.
  - No ML, no prediction models, no live timing.
  - All conclusions are descriptive, not predictive.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.models.driver import Driver
from app.models.favorite_driver import FavoriteDriver
from app.models.lap import Lap
from app.models.race_control_message import RaceControlMessage
from app.models.session import Session as RaceSession
from app.models.stint import Stint
from app.models.user import User
from app.models.weather_sample import WeatherSample

# Maximum number of strategy-relevant RC messages to include
_MAX_STRATEGY_RC = 25

# Gap in laps below which two pit events are considered the same window
_PIT_WINDOW_CLUSTER_GAP = 6

# Flags that indicate a strategy-relevant race control event
_STRATEGY_FLAGS = {"YELLOW", "DOUBLE YELLOW", "RED", "SAFETY CAR"}

# Keywords that make an RC message strategy-relevant
_STRATEGY_KEYWORDS = [
    "SAFETY CAR", "VSC", "VIRTUAL SAFETY CAR",
    "RED FLAG",
    "PIT LANE OPEN", "PIT LANE CLOSED",
    "RISK OF RAIN", "WEATHER",
    "MEDICAL CAR",
    "RETIRED",
]

# Tyre compounds that indicate a wet-weather strategy
_WET_COMPOUNDS = {"INTERMEDIATE", "WET"}

# Fraction of stints missing lap ranges above which the completeness warning fires
_INSIGHT_COMPLETENESS_THRESHOLD = 0.3


# ─── Public data structures ───────────────────────────────────────────────────

@dataclass
class CompoundUsage:
    """Aggregate usage stats for one tyre compound across all drivers."""
    compound: str
    stint_count: int              # total stints on this compound
    driver_count: int             # distinct drivers who used it
    avg_stint_laps: float | None  # average stint length; None if lap ranges unavailable


@dataclass
class StintDetail:
    """Full detail for one stint, including a derived lap count."""
    stint_number: int | None
    compound: str | None
    lap_start: int | None
    lap_end: int | None
    tyre_age_at_start: int | None
    stint_laps: int | None    # lap_end - lap_start + 1; None if either bound is missing


@dataclass
class DriverStrategy:
    """All strategy data for one driver."""
    driver_number: int
    driver_name: str
    stop_count: int                  # pit stops = len(stints) - 1
    compound_sequence: list[str]     # ordered compound names, e.g. ["MEDIUM", "HARD"]
    stints: list[StintDetail]
    longest_stint_laps: int | None
    is_favourite: bool = False


@dataclass
class PitWindow:
    """A cluster of pit stops happening around the same lap range."""
    window_number: int   # 1-based
    lap_min: int         # earliest pit lap in this cluster
    lap_max: int         # latest pit lap in this cluster
    driver_count: int    # how many drivers pitted in this window


@dataclass
class StrategyRCEvent:
    """A single strategy-relevant race control message."""
    lap_number: int | None
    flag: str | None
    message: str


@dataclass
class WeatherContext:
    """Weather conditions relevant to strategy decisions."""
    had_rain: bool
    wet_tyre_drivers: list[str]   # driver names who used INTERMEDIATE or WET
    air_min: float | None
    air_max: float | None
    track_min: float | None
    track_max: float | None
    sample_count: int
    # Latest reading — the most recent sample in the session
    latest_air_temp: float | None = None
    latest_track_temp: float | None = None
    latest_rainfall: bool | None = None


@dataclass
class StrategyDashboardSummary:
    """
    Complete strategy dashboard payload for one session.
    has_X flags allow callers to render appropriate empty states
    without inspecting list lengths.
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

    # ── Data availability ─────────────────────────────────────────────────────
    has_stint_data: bool
    has_lap_data: bool
    has_rc_data: bool
    has_weather_data: bool

    # ── Compound overview ─────────────────────────────────────────────────────
    compound_usage: list[CompoundUsage] = field(default_factory=list)

    # ── Per-driver strategies ─────────────────────────────────────────────────
    driver_strategies: list[DriverStrategy] = field(default_factory=list)

    # ── Stop-count grouping ───────────────────────────────────────────────────
    # Maps stop_count → sorted list of driver names
    stop_count_groups: dict[int, list[str]] = field(default_factory=dict)

    # ── Pit windows ───────────────────────────────────────────────────────────
    pit_windows: list[PitWindow] = field(default_factory=list)

    # ── Strategy-relevant race control ────────────────────────────────────────
    strategy_rc_events: list[StrategyRCEvent] = field(default_factory=list)

    # ── Weather ───────────────────────────────────────────────────────────────
    weather_context: WeatherContext | None = None

    # ── Personalisation ───────────────────────────────────────────────────────
    favourite_driver_numbers: set[int] = field(default_factory=set)

    # ── Rule-based insights ───────────────────────────────────────────────────
    insights: list[str] = field(default_factory=list)


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


def _stint_laps(s: Stint) -> int | None:
    """Derive lap count for a stint from its stored lap range."""
    if s.lap_start is not None and s.lap_end is not None:
        return s.lap_end - s.lap_start + 1
    return None


def _build_compound_usage(stints: list[Stint]) -> list[CompoundUsage]:
    """
    Build per-compound aggregate stats, sorted by stint_count descending.
    Stints with no compound value are skipped.
    """
    by_compound: dict[str, list[Stint]] = defaultdict(list)
    for s in stints:
        if s.compound:
            by_compound[s.compound].append(s)

    usage: list[CompoundUsage] = []
    for compound, stint_list in by_compound.items():
        drivers = {s.driver_number for s in stint_list}
        valid_counts = [c for c in (_stint_laps(s) for s in stint_list) if c is not None]
        avg = round(sum(valid_counts) / len(valid_counts), 1) if valid_counts else None
        usage.append(CompoundUsage(
            compound=compound,
            stint_count=len(stint_list),
            driver_count=len(drivers),
            avg_stint_laps=avg,
        ))

    usage.sort(key=lambda c: c.stint_count, reverse=True)
    return usage


def _build_driver_strategies(
    stints: list[Stint],
    names: dict[int, str],
    favs: set[int],
) -> tuple[list[DriverStrategy], dict[int, list[str]]]:
    """
    Build per-driver strategy entries and a stop-count grouping dict.

    Returns (driver_strategies sorted by driver_number, stop_count_groups).
    stop_count_groups maps stop_count → sorted list of driver names.
    """
    by_driver: dict[int, list[Stint]] = defaultdict(list)
    for s in stints:
        by_driver[s.driver_number].append(s)

    strategies: list[DriverStrategy] = []
    stop_groups: dict[int, list[str]] = defaultdict(list)

    for dn in sorted(by_driver):
        driver_stints = sorted(
            by_driver[dn],
            key=lambda s: (s.stint_number or 0, s.lap_start or 0),
        )
        compound_seq = [s.compound for s in driver_stints if s.compound]
        details = [
            StintDetail(
                stint_number=s.stint_number,
                compound=s.compound,
                lap_start=s.lap_start,
                lap_end=s.lap_end,
                tyre_age_at_start=s.tyre_age_at_start,
                stint_laps=_stint_laps(s),
            )
            for s in driver_stints
        ]
        valid_counts = [d.stint_laps for d in details if d.stint_laps is not None]
        stop_count = max(0, len(driver_stints) - 1)
        driver_name = names.get(dn, f"Driver #{dn}")

        strategies.append(DriverStrategy(
            driver_number=dn,
            driver_name=driver_name,
            stop_count=stop_count,
            compound_sequence=compound_seq,
            stints=details,
            longest_stint_laps=max(valid_counts) if valid_counts else None,
            is_favourite=dn in favs,
        ))
        stop_groups[stop_count].append(driver_name)

    return strategies, {k: sorted(v) for k, v in stop_groups.items()}


def _cluster_pit_laps(pit_laps: list[int], gap: int = _PIT_WINDOW_CLUSTER_GAP) -> list[PitWindow]:
    """
    Group a sorted list of pit lap numbers into windows.
    Consecutive values within `gap` laps of each other belong to the same window.
    """
    if not pit_laps:
        return []

    windows: list[PitWindow] = []
    current: list[int] = [pit_laps[0]]

    for lap in pit_laps[1:]:
        if lap - current[-1] <= gap:
            current.append(lap)
        else:
            windows.append(PitWindow(
                window_number=len(windows) + 1,
                lap_min=current[0],
                lap_max=current[-1],
                driver_count=len(current),
            ))
            current = [lap]

    windows.append(PitWindow(
        window_number=len(windows) + 1,
        lap_min=current[0],
        lap_max=current[-1],
        driver_count=len(current),
    ))
    return windows


def _derive_pit_windows(stints: list[Stint]) -> list[PitWindow]:
    """
    Derive pit stop windows from stint data.

    For each driver, lap_start of their 2nd+ stints approximates when
    they pitted. Collect all such laps, sort, and cluster by proximity.
    """
    by_driver: dict[int, list[Stint]] = defaultdict(list)
    for s in stints:
        by_driver[s.driver_number].append(s)

    pit_laps: list[int] = []
    for driver_stints in by_driver.values():
        ordered = sorted(
            driver_stints,
            key=lambda s: (s.stint_number or 0, s.lap_start or 0),
        )
        # Skip the first stint — only transitions represent pit stops
        for s in ordered[1:]:
            if s.lap_start is not None:
                pit_laps.append(s.lap_start)

    return _cluster_pit_laps(sorted(pit_laps))


def _build_strategy_rc_events(
    rc_messages: list[RaceControlMessage],
) -> list[StrategyRCEvent]:
    """
    Filter RC messages to strategy-relevant events only.
    BLUE flag (lapping) messages are always excluded.
    Result is capped at _MAX_STRATEGY_RC and kept in chronological order.
    """
    _epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)

    selected: list[RaceControlMessage] = []
    for msg in rc_messages:
        flag = (msg.flag or "").upper()
        text = (msg.message or "").upper()

        if flag == "BLUE":
            continue

        if flag in _STRATEGY_FLAGS or any(kw in text for kw in _STRATEGY_KEYWORDS):
            selected.append(msg)

    selected.sort(key=lambda m: m.date or _epoch)
    selected = selected[:_MAX_STRATEGY_RC]

    return [
        StrategyRCEvent(
            lap_number=m.lap_number,
            flag=m.flag,
            message=m.message or "",
        )
        for m in selected
    ]


def _build_weather_context(
    session_id: int,
    db: DBSession,
    stints: list[Stint],
    names: dict[int, str],
) -> WeatherContext | None:
    """
    Build weather context including which drivers used wet-weather tyres.
    Returns None when no weather samples are stored for this session.
    """
    samples = (
        db.query(WeatherSample)
        .filter(WeatherSample.session_id == session_id)
        .all()
    )
    if not samples:
        return None

    air = [s.air_temperature for s in samples if s.air_temperature is not None]
    track = [s.track_temperature for s in samples if s.track_temperature is not None]

    wet_drivers: list[str] = sorted({
        names.get(s.driver_number, f"Driver #{s.driver_number}")
        for s in stints
        if (s.compound or "").upper() in _WET_COMPOUNDS
    })

    # Latest sample — prefer the one with the highest timestamp
    dated = [s for s in samples if s.date is not None]
    latest = max(dated, key=lambda s: s.date) if dated else samples[-1]

    def _r1(v: float | None) -> float | None:
        return round(v, 1) if v is not None else None

    return WeatherContext(
        had_rain=any(s.rainfall for s in samples),
        wet_tyre_drivers=wet_drivers,
        air_min=round(min(air), 1) if air else None,
        air_max=round(max(air), 1) if air else None,
        track_min=round(min(track), 1) if track else None,
        track_max=round(max(track), 1) if track else None,
        sample_count=len(samples),
        latest_air_temp=_r1(latest.air_temperature),
        latest_track_temp=_r1(latest.track_temperature),
        latest_rainfall=latest.rainfall,
    )


def _generate_insights(
    has_stint_data: bool,
    driver_strategies: list[DriverStrategy],
    compound_usage: list[CompoundUsage],
    weather_context: WeatherContext | None,
) -> list[str]:
    """
    Produce plain-English, rule-based insight strings from pre-computed data.

    Every sentence is descriptive — it states what the stored data shows.
    No predictions, no ML, no external knowledge.
    """
    if not has_stint_data:
        return [
            "No stint data is available for this session — "
            "strategy insights cannot be generated."
        ]

    insights: list[str] = []

    # ── Data completeness check ───────────────────────────────────────────────
    all_stints = [s for ds in driver_strategies for s in ds.stints]
    missing_ranges = sum(1 for s in all_stints if s.stint_laps is None)
    if all_stints and missing_ranges / len(all_stints) > _INSIGHT_COMPLETENESS_THRESHOLD:
        insights.append(
            f"Strategy insights are limited because stint data is incomplete "
            f"({missing_ranges} of {len(all_stints)} stints are missing lap numbers)."
        )

    # ── Most used compound ────────────────────────────────────────────────────
    if compound_usage:
        top = compound_usage[0]  # already sorted by stint_count desc
        driver_word = "driver" if top.driver_count == 1 else "drivers"
        avg_str = f" averaging {top.avg_stint_laps} laps per stint" if top.avg_stint_laps else ""
        insights.append(
            f"{top.compound} was the most used compound — "
            f"{top.stint_count} stints across {top.driver_count} {driver_word}{avg_str}."
        )

    # ── Driver with the most stints ────────────────────────────────────────────
    if driver_strategies:
        max_count = max(len(ds.stints) for ds in driver_strategies)
        most_stints = [ds for ds in driver_strategies if len(ds.stints) == max_count]
        if max_count > 1:
            if len(most_stints) == 1:
                ds = most_stints[0]
                seq = " → ".join(ds.compound_sequence) if ds.compound_sequence else "unknown compounds"
                insights.append(
                    f"{ds.driver_name} used the most stints ({max_count}): {seq}."
                )
            else:
                names = ", ".join(ds.driver_name for ds in most_stints[:3])
                suffix = f" and {len(most_stints) - 3} more" if len(most_stints) > 3 else ""
                insights.append(
                    f"{len(most_stints)} drivers each used {max_count} stints, "
                    f"including {names}{suffix}."
                )

    # ── Longest single stint ──────────────────────────────────────────────────
    best_ds: DriverStrategy | None = None
    best_laps = 0
    for ds in driver_strategies:
        if ds.longest_stint_laps and ds.longest_stint_laps > best_laps:
            best_laps = ds.longest_stint_laps
            best_ds = ds

    if best_ds and best_laps > 0:
        best_stint = max(best_ds.stints, key=lambda s: s.stint_laps or 0)
        compound_str = f" on {best_stint.compound}" if best_stint.compound else ""
        insights.append(
            f"{best_ds.driver_name} ran the longest stint: {best_laps} laps{compound_str}."
        )

    # ── Multi-compound vs single-compound split ───────────────────────────────
    multi = [ds for ds in driver_strategies if len({c for c in ds.compound_sequence if c}) > 1]
    single = [ds for ds in driver_strategies if len({c for c in ds.compound_sequence if c}) == 1]

    if multi and single:
        insights.append(
            f"{len(multi)} driver{'s' if len(multi) != 1 else ''} used multiple compounds; "
            f"{len(single)} ran a single compound throughout."
        )
    elif single and not multi:
        insights.append(f"All {len(single)} drivers ran a single compound throughout the session.")
    elif multi and not single:
        insights.append(f"All {len(multi)} drivers changed compounds during the session.")

    # Name single-compound drivers individually when there are few enough
    if 1 <= len(single) <= 5:
        named = ", ".join(
            f"{ds.driver_name} ({ds.compound_sequence[0]})"
            for ds in single
            if ds.compound_sequence
        )
        if named:
            insights.append(f"Single-compound drivers: {named}.")

    # ── Wet tyre usage ────────────────────────────────────────────────────────
    if weather_context and weather_context.wet_tyre_drivers:
        names = ", ".join(weather_context.wet_tyre_drivers)
        insights.append(f"Wet-weather tyres (Intermediate/Wet) were used by: {names}.")

    # ── Rain with no wet-tyre record ──────────────────────────────────────────
    if weather_context and weather_context.had_rain and not weather_context.wet_tyre_drivers:
        insights.append(
            "Rain was recorded during the session, though no wet-weather compounds "
            "appear in the stored stint data — conditions may have been relevant to strategy."
        )

    # ── Significant track-temperature variance ────────────────────────────────
    if (
        weather_context
        and weather_context.track_min is not None
        and weather_context.track_max is not None
        and weather_context.track_max - weather_context.track_min >= 10
    ):
        insights.append(
            f"Track temperature varied between {weather_context.track_min}–"
            f"{weather_context.track_max}°C during the session, "
            f"which could be relevant to tyre behaviour and degradation."
        )

    return insights


# ─── Public API ───────────────────────────────────────────────────────────────

def build_strategy_summary(
    session: RaceSession,
    db: DBSession,
    current_user: User | None = None,
) -> StrategyDashboardSummary:
    """
    Build a complete strategy summary for one session.

    Pass current_user to enable favourite-driver highlighting; pass None
    for unauthenticated callers (is_favourite fields default to False).

    All conclusions are descriptive from stored data — no ML, no predictions.
    """
    names = _driver_name_map(db)
    favs = _favourite_numbers(current_user, db)
    race_name = session.race.name if session.race else f"Race {session.race_id}"

    # ── Stints ────────────────────────────────────────────────────────────────
    stints = (
        db.query(Stint)
        .filter(Stint.session_id == session.id)
        .order_by(Stint.driver_number, Stint.stint_number)
        .all()
    )
    has_stint_data = len(stints) > 0

    compound_usage: list[CompoundUsage] = []
    driver_strategies: list[DriverStrategy] = []
    stop_count_groups: dict[int, list[str]] = {}
    pit_windows: list[PitWindow] = []

    if has_stint_data:
        compound_usage = _build_compound_usage(stints)
        driver_strategies, stop_count_groups = _build_driver_strategies(stints, names, favs)
        pit_windows = _derive_pit_windows(stints)

    # ── Lap data availability ─────────────────────────────────────────────────
    lap_count: int = (
        db.query(func.count(Lap.id))
        .filter(Lap.session_id == session.id)
        .scalar()
    ) or 0
    has_lap_data = lap_count > 0

    # ── Race control ──────────────────────────────────────────────────────────
    rc_all = (
        db.query(RaceControlMessage)
        .filter(RaceControlMessage.session_id == session.id)
        .order_by(RaceControlMessage.date)
        .all()
    )
    has_rc_data = len(rc_all) > 0
    strategy_rc_events = _build_strategy_rc_events(rc_all) if rc_all else []

    # ── Weather ───────────────────────────────────────────────────────────────
    weather_context = _build_weather_context(session.id, db, stints, names)
    has_weather_data = weather_context is not None

    # ── Rule-based insights ───────────────────────────────────────────────────
    insights = _generate_insights(
        has_stint_data=has_stint_data,
        driver_strategies=driver_strategies,
        compound_usage=compound_usage,
        weather_context=weather_context,
    )

    return StrategyDashboardSummary(
        session_id=session.id,
        session_name=session.session_name,
        session_type=session.session_type,
        race_name=race_name,
        circuit_short_name=session.circuit_short_name,
        country_name=session.country_name,
        start_time=session.start_time,
        is_synced=session.openf1_session_key is not None,
        has_stint_data=has_stint_data,
        has_lap_data=has_lap_data,
        has_rc_data=has_rc_data,
        has_weather_data=has_weather_data,
        compound_usage=compound_usage,
        driver_strategies=driver_strategies,
        stop_count_groups=stop_count_groups,
        pit_windows=pit_windows,
        strategy_rc_events=strategy_rc_events,
        weather_context=weather_context,
        favourite_driver_numbers=favs,
        insights=insights,
    )


def get_strategy_summary(
    session_id: int,
    db: DBSession,
    current_user: User | None = None,
) -> StrategyDashboardSummary | None:
    """
    Convenience wrapper for API endpoints.
    Returns None if the session does not exist.
    """
    session = db.query(RaceSession).filter(RaceSession.id == session_id).first()
    if session is None:
        return None
    return build_strategy_summary(session, db, current_user)


def format_strategy_context_lines(summary: StrategyDashboardSummary) -> list[str]:
    """
    Produce compact context lines for the AI context builder.

    Designed to be imported by ai_context.py without coupling it to the
    internal helpers in this module. Returns an empty list when no stint
    data is available so callers can emit a missing-data flag instead.
    """
    if not summary.has_stint_data:
        return [f"[{summary.session_name}] Missing: no_stint_data"]

    lines: list[str] = [
        f"[{summary.session_name} — {summary.race_name}] Strategy summary:"
    ]

    # Compound usage
    if summary.compound_usage:
        parts: list[str] = []
        for cu in summary.compound_usage:
            part = f"{cu.compound}×{cu.stint_count} stints ({cu.driver_count} drivers"
            if cu.avg_stint_laps is not None:
                part += f", avg {cu.avg_stint_laps} laps"
            part += ")"
            parts.append(part)
        lines.append("  Compound usage: " + ", ".join(parts))

    # Stop-count grouping
    if summary.stop_count_groups:
        for stops in sorted(summary.stop_count_groups):
            drivers = summary.stop_count_groups[stops]
            label = "stop" if stops == 1 else "stops"
            lines.append(f"  {stops} {label}: {', '.join(drivers)}")

    # Pit windows
    if summary.pit_windows:
        parts = []
        for pw in summary.pit_windows:
            if pw.lap_min == pw.lap_max:
                parts.append(f"Window {pw.window_number}: lap {pw.lap_min} ({pw.driver_count} drivers)")
            else:
                parts.append(f"Window {pw.window_number}: laps {pw.lap_min}–{pw.lap_max} ({pw.driver_count} drivers)")
        lines.append("  Pit windows: " + "; ".join(parts))

    # Strategy RC events
    if summary.strategy_rc_events:
        lines.append("  Strategy events:")
        for ev in summary.strategy_rc_events:
            lap_str = f" [Lap {ev.lap_number}]" if ev.lap_number else ""
            lines.append(f"    •{lap_str} {ev.message}")

    # Weather context
    if summary.weather_context:
        wc = summary.weather_context
        rain_str = "rain recorded" if wc.had_rain else "no rain"
        air_str = (
            f"air {wc.air_min}–{wc.air_max}°C"
            if wc.air_min is not None and wc.air_max is not None
            else ""
        )
        lines.append("  Weather: " + rain_str + (f", {air_str}" if air_str else ""))
        if wc.wet_tyre_drivers:
            lines.append(f"  Wet tyres used by: {', '.join(wc.wet_tyre_drivers)}")

    return lines
