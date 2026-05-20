"""
session_dashboard.py

Single source of truth for building a structured session summary from stored
GridPulse data. Used by:
  - GET /sessions/{id}/dashboard  (API endpoint, Phase 12)
  - The AI context builder (planned refactor — currently ai_context.py
    duplicates some of this logic but will eventually import from here)

Design rules:
  - Summarise everything — never return raw row dumps.
  - Handle missing data gracefully — every section has a has_X flag.
  - Keep helper functions small and focused.
  - No analytics, no strategy calculations, no track maps.
"""

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session as DBSession

from app.models.driver import Driver
from app.models.favorite_driver import FavoriteDriver
from app.models.lap import Lap
from app.models.race_control_message import RaceControlMessage
from app.models.session import Session as RaceSession
from app.models.stint import Stint
from app.models.user import User
from app.models.weather_sample import WeatherSample

# Maximum number of race control messages in the curated list.
# Blue-flag (lapping) messages are excluded entirely before this cap applies.
_MAX_RC_CURATED = 40

# ── RC classification constants ───────────────────────────────────────────────

# Flags worth including in the curated list (high priority)
_RC_PRIORITY_FLAGS = {"GREEN", "YELLOW", "DOUBLE YELLOW", "RED", "CHEQUERED", "SAFETY CAR"}

# Flags to always exclude (lapping notifications — repetitive, low information)
_RC_EXCLUDE_FLAGS = {"BLUE"}

# Keywords that make a message worth including even without a priority flag
_RC_IMPORTANT_KEYWORDS = [
    "VSC", "VIRTUAL SAFETY CAR", "SAFETY CAR", "MEDICAL CAR",
    "INVESTIGATE", "PENALTY", "DRIVE THROUGH", "STOP AND GO", "STOP-AND-GO",
    "RETIRED", "INCIDENT", "SESSION STARTED", "SESSION FINISHED",
    "PIT EXIT", "PIT LANE", "MARSHALS", "RISK OF RAIN",
    "CHEQUERED FLAG", "OVERTAKE ENABLED", "OVERTAKE DISABLED",
    "TIME DELETED", "TRACK LIMITS",
]

# Ordered patterns for key-events extraction (first match wins per label)
_RC_KEY_EVENT_PATTERNS = [
    ("SAFETY CAR DEPLOYED", "Safety car deployed"),
    ("SAFETY CAR IN",       "Safety car recalled"),
    # OpenF1 stores VSC as "VSC DEPLOYED" not "VIRTUAL SAFETY CAR"
    ("VSC DEPLOYED",        "Virtual safety car (VSC)"),
    ("VIRTUAL SAFETY CAR",  "Virtual safety car (VSC)"),
    ("RED FLAG",            "Red flag"),
    # OpenF1 stores DRS as "OVERTAKE ENABLED/DISABLED"
    ("OVERTAKE ENABLED",    "DRS enabled"),
    ("OVERTAKE DISABLED",   "DRS disabled"),
    ("DRS ENABLED",         "DRS enabled"),
    ("DRS DISABLED",        "DRS disabled"),
    ("PIT LANE OPEN",       "Pit lane open"),
    ("PIT LANE CLOSED",     "Pit lane closed"),
    ("INVESTIGATE",         "Investigation / penalty"),
    ("PENALTY",             "Penalty"),
    ("DRIVE THROUGH",       "Drive-through penalty"),
    ("STOP AND GO",         "Stop-and-go penalty"),
    ("STOP-AND-GO",         "Stop-and-go penalty"),
    ("RETIRED",             "Retirement"),
    ("MEDICAL CAR",         "Medical car deployed"),
]


# ─── Public data structures ───────────────────────────────────────────────────

@dataclass
class LapStats:
    """Aggregate lap counts — no individual lap rows exposed."""
    total_rows: int          # total lap rows stored for this session
    driver_count: int        # distinct drivers with lap data
    max_lap: int | None      # highest lap number seen across all drivers


@dataclass
class FinishingEntry:
    """One row in the derived leaderboard."""
    position: int
    driver_number: int
    driver_name: str
    max_lap: int             # highest lap number this driver has a row for
    row_count: int           # total lap rows for this driver
    laps_behind: int         # 0 for lead-lap finishers
    is_favourite: bool = False


@dataclass
class StintEntry:
    """One stint for one driver."""
    stint_number: int | None
    compound: str | None
    lap_start: int | None
    lap_end: int | None
    tyre_age_at_start: int | None


@dataclass
class DriverStintSummary:
    """All stints for one driver."""
    driver_number: int
    driver_name: str
    stints: list[StintEntry] = field(default_factory=list)
    is_favourite: bool = False


@dataclass
class KeyRCEvent:
    """A single notable race control event extracted from the message log."""
    label: str
    lap_number: int | None


@dataclass
class RCMessageSummary:
    """One race control message, safe to include verbatim."""
    lap_number: int | None
    flag: str | None
    message: str


@dataclass
class LatestWeatherSample:
    """Raw values from the most recent weather reading in the session."""
    air_temperature: float | None
    track_temperature: float | None
    humidity: float | None       # percentage, 0–100
    rainfall: bool | None
    wind_speed: float | None     # metres per second
    wind_direction: int | None   # degrees: 0 = N, 90 = E, 180 = S, 270 = W


@dataclass
class WeatherSummary:
    """Temperature range, rainfall flag, and latest reading from weather samples."""
    air_min: float | None
    air_max: float | None
    track_min: float | None
    track_max: float | None
    had_rain: bool
    sample_count: int
    latest_sample: LatestWeatherSample | None = None


@dataclass
class SessionDashboardSummary:
    """
    Complete dashboard payload for one session.
    Every section has a has_X flag so callers can render appropriate
    empty states without inspecting list lengths.
    """
    # ── Identity ──────────────────────────────────────────────────────────────
    session_id: int
    session_name: str
    session_type: str        # "race", "sprint", "qualifying", "fp1", …
    race_name: str
    circuit_short_name: str | None
    country_name: str | None
    start_time: datetime | None
    is_synced: bool          # True when openf1_session_key is set

    # ── Laps ──────────────────────────────────────────────────────────────────
    lap_stats: LapStats
    has_lap_data: bool

    # Leaderboard — populated for race/sprint only; empty list otherwise
    finishing_order: list[FinishingEntry] = field(default_factory=list)

    # ── Tyres ─────────────────────────────────────────────────────────────────
    compound_overview: dict[str, int] = field(default_factory=dict)
    stint_summary: list[DriverStintSummary] = field(default_factory=list)
    has_stint_data: bool = False

    # ── Race control ──────────────────────────────────────────────────────────
    key_rc_events: list[KeyRCEvent] = field(default_factory=list)
    rc_messages: list[RCMessageSummary] = field(default_factory=list)
    rc_total: int = 0                # total messages stored
    rc_blue_flag_count: int = 0      # blue-flag messages excluded from curated list
    rc_omitted_count: int = 0        # non-blue messages omitted due to cap
    has_rc_data: bool = False

    # ── Weather ───────────────────────────────────────────────────────────────
    weather: WeatherSummary | None = None
    has_weather_data: bool = False

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


def _build_finishing_order(
    session_id: int,
    session_type: str,
    db: DBSession,
    names: dict[int, str],
    favs: set[int],
) -> list[FinishingEntry]:
    """
    Derive an approximate finishing order from lap data.

    Method: sort by max lap_number DESC (not row count — OpenF1 sometimes
    omits lap rows for some drivers). Tiebreaker: date_start of the final
    recorded lap ASC (earlier = crossed the line first).

    Only meaningful for race and sprint sessions; returns [] otherwise.
    """
    if session_type not in ("race", "sprint"):
        return []

    laps = db.query(Lap).filter(Lap.session_id == session_id).all()
    if not laps:
        return []

    # Per-driver: (max_lap_number, date_start_of_that_lap, total_row_count)
    driver_data: dict[int, tuple[int, datetime | None, int]] = {}
    for lap in laps:
        dn = lap.driver_number
        if dn not in driver_data:
            driver_data[dn] = (lap.lap_number, lap.date_start, 1)
        elif lap.lap_number > driver_data[dn][0]:
            driver_data[dn] = (lap.lap_number, lap.date_start, driver_data[dn][2] + 1)
        else:
            driver_data[dn] = (driver_data[dn][0], driver_data[dn][1], driver_data[dn][2] + 1)

    _far_future = datetime(9999, 1, 1, tzinfo=timezone.utc)
    ordered = sorted(
        driver_data.keys(),
        key=lambda dn: (
            -driver_data[dn][0],                         # higher max lap = ahead
            driver_data[dn][1] or _far_future,           # earlier final-lap start = ahead
        ),
    )

    race_max_lap = max(v[0] for v in driver_data.values())

    result: list[FinishingEntry] = []
    for pos, dn in enumerate(ordered, 1):
        max_lap, _, row_count = driver_data[dn]
        result.append(FinishingEntry(
            position=pos,
            driver_number=dn,
            driver_name=names.get(dn, f"Driver #{dn}"),
            max_lap=max_lap,
            row_count=row_count,
            laps_behind=race_max_lap - max_lap,
            is_favourite=dn in favs,
        ))
    return result


def _build_stint_summary(
    session_id: int,
    db: DBSession,
    names: dict[int, str],
    favs: set[int],
) -> tuple[dict[str, int], list[DriverStintSummary]]:
    """
    Returns (compound_overview, per_driver_summaries).
    compound_overview: e.g. {"HARD": 22, "MEDIUM": 18, "SOFT": 13}
    """
    stints = (
        db.query(Stint)
        .filter(Stint.session_id == session_id)
        .order_by(Stint.driver_number, Stint.stint_number)
        .all()
    )
    if not stints:
        return {}, []

    compound_counts: Counter = Counter(s.compound for s in stints if s.compound)

    driver_stints: dict[int, list[Stint]] = defaultdict(list)
    for s in stints:
        driver_stints[s.driver_number].append(s)

    summaries: list[DriverStintSummary] = []
    for dn in sorted(driver_stints):
        entries = [
            StintEntry(
                stint_number=s.stint_number,
                compound=s.compound,
                lap_start=s.lap_start,
                lap_end=s.lap_end,
                tyre_age_at_start=s.tyre_age_at_start,
            )
            for s in driver_stints[dn]
        ]
        summaries.append(DriverStintSummary(
            driver_number=dn,
            driver_name=names.get(dn, f"Driver #{dn}"),
            stints=entries,
            is_favourite=dn in favs,
        ))

    return dict(compound_counts), summaries


def _extract_key_rc_events(rc_messages: list) -> list[KeyRCEvent]:
    """
    Scan all RC messages and return one bullet per notable event type,
    recording the lap number of the first occurrence.
    """
    seen: set[str] = set()
    events: list[KeyRCEvent] = []

    for msg in rc_messages:
        combined = ((msg.message or "") + " " + (msg.flag or "")).upper()
        for pattern, label in _RC_KEY_EVENT_PATTERNS:
            if pattern in combined and label not in seen:
                events.append(KeyRCEvent(label=label, lap_number=msg.lap_number))
                seen.add(label)

    return events


def _curate_rc_messages(
    rc_messages: list,
    max_count: int,
) -> tuple[list[RCMessageSummary], int, int]:
    """
    Smart-select up to max_count messages from the full RC log.

    Priority:
      1. Messages with a non-BLUE priority flag (YELLOW, RED, GREEN, etc.)
         or a keyword match (VSC, investigation, penalty, pit lane, etc.)
      2. Everything else (CLEAR flags, routine session messages)

    BLUE flag messages (lapping) are always excluded — they are repetitive
    and low-information; the key-events summary captures what matters.

    Returns (curated_summaries, omitted_non_blue_count, blue_flag_count).
    """
    _epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)

    blue_count = 0
    high: list = []   # priority messages
    low: list = []    # routine messages (not blue, not high priority)

    for msg in rc_messages:
        flag = (msg.flag or "").upper()
        text = (msg.message or "").upper()

        if flag in _RC_EXCLUDE_FLAGS:
            blue_count += 1
            continue

        if flag in _RC_PRIORITY_FLAGS or any(kw in text for kw in _RC_IMPORTANT_KEYWORDS):
            high.append(msg)
        else:
            low.append(msg)

    # Fill cap: high-priority first, then low-priority for remaining slots
    selected = high[:max_count]
    remaining_slots = max_count - len(selected)
    if remaining_slots > 0:
        selected += low[:remaining_slots]

    # Restore chronological order
    selected.sort(key=lambda m: m.date or _epoch)

    non_blue_total = len(high) + len(low)
    omitted = non_blue_total - len(selected)

    summaries = [
        RCMessageSummary(
            lap_number=m.lap_number,
            flag=m.flag,
            message=m.message or "",
        )
        for m in selected
    ]
    return summaries, omitted, blue_count


def _build_weather_summary(session_id: int, db: DBSession) -> WeatherSummary | None:
    """Aggregate weather samples into a summary with range stats and latest reading."""
    samples = (
        db.query(WeatherSample)
        .filter(WeatherSample.session_id == session_id)
        .all()
    )
    if not samples:
        return None

    air = [s.air_temperature for s in samples if s.air_temperature is not None]
    track = [s.track_temperature for s in samples if s.track_temperature is not None]

    # Latest reading: prefer the sample with the highest timestamp; fall back to
    # the last element when all dates are null (shouldn't happen in practice).
    dated = [s for s in samples if s.date is not None]
    latest_raw = max(dated, key=lambda s: s.date) if dated else samples[-1]

    def _r1(v: float | None) -> float | None:
        return round(v, 1) if v is not None else None

    latest = LatestWeatherSample(
        air_temperature=_r1(latest_raw.air_temperature),
        track_temperature=_r1(latest_raw.track_temperature),
        humidity=round(latest_raw.humidity) if latest_raw.humidity is not None else None,
        rainfall=latest_raw.rainfall,
        wind_speed=_r1(latest_raw.wind_speed),
        wind_direction=latest_raw.wind_direction,
    )

    return WeatherSummary(
        air_min=round(min(air), 1) if air else None,
        air_max=round(max(air), 1) if air else None,
        track_min=round(min(track), 1) if track else None,
        track_max=round(max(track), 1) if track else None,
        had_rain=any(s.rainfall for s in samples),
        sample_count=len(samples),
        latest_sample=latest,
    )


# ─── Public API ───────────────────────────────────────────────────────────────

def build_session_summary(
    session: RaceSession,
    db: DBSession,
    current_user: User | None = None,
) -> SessionDashboardSummary:
    """
    Build a complete dashboard summary for one session.

    Pass current_user to enable favourite-driver highlighting; pass None
    for unauthenticated callers (highlighting fields default to False).

    All heavy computation (finishing order, stint grouping, RC curation)
    happens here so that callers — whether the API endpoint or the AI
    context builder — receive clean, structured data with no raw DB rows.
    """
    names = _driver_name_map(db)
    favs = _favourite_numbers(current_user, db)

    race_name = session.race.name if session.race else f"Race {session.race_id}"

    # ── Lap stats (aggregate queries — no row dumps) ──────────────────────────
    total_rows: int = (
        db.query(func.count(Lap.id))
        .filter(Lap.session_id == session.id)
        .scalar()
    ) or 0

    driver_count: int = (
        db.query(func.count(distinct(Lap.driver_number)))
        .filter(Lap.session_id == session.id)
        .scalar()
    ) or 0

    max_lap: int | None = (
        db.query(func.max(Lap.lap_number))
        .filter(Lap.session_id == session.id)
        .scalar()
    )

    lap_stats = LapStats(
        total_rows=total_rows,
        driver_count=driver_count,
        max_lap=max_lap,
    )

    # ── Leaderboard ───────────────────────────────────────────────────────────
    finishing_order = _build_finishing_order(
        session.id, session.session_type, db, names, favs
    )

    # ── Tyres / stints ────────────────────────────────────────────────────────
    compound_overview, stint_summary = _build_stint_summary(
        session.id, db, names, favs
    )

    # ── Race control ──────────────────────────────────────────────────────────
    rc_all = (
        db.query(RaceControlMessage)
        .filter(RaceControlMessage.session_id == session.id)
        .order_by(RaceControlMessage.date)
        .all()
    )

    key_rc_events: list[KeyRCEvent] = []
    rc_messages: list[RCMessageSummary] = []
    rc_omitted = 0
    rc_blue = 0

    if rc_all:
        key_rc_events = _extract_key_rc_events(rc_all)
        rc_messages, rc_omitted, rc_blue = _curate_rc_messages(rc_all, _MAX_RC_CURATED)

    # ── Weather ───────────────────────────────────────────────────────────────
    weather = _build_weather_summary(session.id, db)

    return SessionDashboardSummary(
        session_id=session.id,
        session_name=session.session_name,
        session_type=session.session_type,
        race_name=race_name,
        circuit_short_name=session.circuit_short_name,
        country_name=session.country_name,
        start_time=session.start_time,
        is_synced=session.openf1_session_key is not None,
        lap_stats=lap_stats,
        has_lap_data=total_rows > 0,
        finishing_order=finishing_order,
        compound_overview=compound_overview,
        stint_summary=stint_summary,
        has_stint_data=len(stint_summary) > 0,
        key_rc_events=key_rc_events,
        rc_messages=rc_messages,
        rc_total=len(rc_all),
        rc_blue_flag_count=rc_blue,
        rc_omitted_count=rc_omitted,
        has_rc_data=len(rc_all) > 0,
        weather=weather,
        has_weather_data=weather is not None,
        favourite_driver_numbers=favs,
    )


def get_session_summary(
    session_id: int,
    db: DBSession,
    current_user: User | None = None,
) -> SessionDashboardSummary | None:
    """
    Convenience wrapper for API endpoints.
    Looks up the session and returns None if it does not exist.
    """
    session = db.query(RaceSession).filter(RaceSession.id == session_id).first()
    if session is None:
        return None
    return build_session_summary(session, db, current_user)
