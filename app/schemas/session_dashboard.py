"""
session_dashboard.py (schemas)

Pydantic response models for the GET /sessions/{id}/dashboard endpoint.

These schemas sit between the session_dashboard service (which returns
Python dataclasses) and the HTTP response (which must be JSON).

Design rules:
  - Every field is either a primitive or a nested schema — no raw ORM rows.
  - Sensitive fields (user email, auth tokens) are never included.
  - has_* flags are always present so the frontend can render empty states
    without checking list lengths.
  - Field names match the dataclass names in session_dashboard.py so the
    from_summary() converter stays small.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.services.session_dashboard import SessionDashboardSummary


# ─── Nested schemas (smallest → largest) ─────────────────────────────────────

class DashboardLapStats(BaseModel):
    """Aggregate lap counts for the session — no individual lap rows."""
    total_rows: int         # total lap rows stored
    driver_count: int       # distinct drivers with lap data
    max_lap: int | None     # highest lap number seen across all drivers


class DashboardDriverSummary(BaseModel):
    """One entry in the leaderboard / finishing order."""
    position: int
    driver_number: int
    driver_name: str
    max_lap: int            # highest lap number recorded for this driver
    laps_behind: int        # 0 for lead-lap finishers; >0 = lapped or retired
    is_favourite: bool


class DashboardStintEntry(BaseModel):
    """One stint within a driver's tyre strategy."""
    stint_number: int | None
    compound: str | None    # SOFT / MEDIUM / HARD / INTERMEDIATE / WET
    lap_start: int | None
    lap_end: int | None
    tyre_age_at_start: int | None   # 0 = new; >0 = used laps at start


class DashboardStintSummary(BaseModel):
    """All stints for one driver."""
    driver_number: int
    driver_name: str
    stints: list[DashboardStintEntry]
    is_favourite: bool


class DashboardKeyEvent(BaseModel):
    """A notable event extracted from the race control log."""
    label: str              # e.g. "Safety car deployed", "Virtual safety car (VSC)"
    lap_number: int | None  # first occurrence


class DashboardRCMessage(BaseModel):
    """One curated race control message (blue-flag messages excluded)."""
    lap_number: int | None
    flag: str | None        # e.g. "YELLOW", "DOUBLE YELLOW", "RED", "CHEQUERED"
    message: str


class DashboardRaceControlSummary(BaseModel):
    """
    Complete race control section.

    key_events: high-level summary (no cap — every significant event type).
    messages: curated chronological list (blue-flag messages excluded,
              remaining capped at _MAX_RC_CURATED from the service).
    """
    key_events: list[DashboardKeyEvent]
    messages: list[DashboardRCMessage]
    total: int              # total messages stored for this session
    blue_flag_count: int    # blue-flag messages excluded from `messages`
    omitted_count: int      # non-blue messages omitted due to cap


class DashboardWeatherSummary(BaseModel):
    """Min / max temperature and rainfall flag across all weather samples."""
    air_min: float | None
    air_max: float | None
    track_min: float | None
    track_max: float | None
    had_rain: bool
    sample_count: int


# ─── Top-level response ───────────────────────────────────────────────────────

class SessionDashboardResponse(BaseModel):
    """
    Full dashboard payload for one session.

    Returned by GET /sessions/{id}/dashboard.
    Every data section has a has_* flag — callers should check these before
    rendering cards so they can show appropriate empty states.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    session_id: int
    session_name: str
    session_type: str           # "race", "sprint", "qualifying", "fp1", …
    race_name: str
    circuit_short_name: str | None
    country_name: str | None
    start_time: datetime | None
    is_synced: bool             # False when no OpenF1 data has been ingested

    # ── Availability flags ────────────────────────────────────────────────────
    has_lap_data: bool
    has_stint_data: bool
    has_rc_data: bool
    has_weather_data: bool

    # ── Lap stats ─────────────────────────────────────────────────────────────
    lap_stats: DashboardLapStats

    # ── Leaderboard (race / sprint only; empty list for other session types) ──
    finishing_order: list[DashboardDriverSummary]

    # ── Tyres ─────────────────────────────────────────────────────────────────
    compound_overview: dict[str, int]       # e.g. {"HARD": 23, "MEDIUM": 12}
    stint_summary: list[DashboardStintSummary]

    # ── Race control ──────────────────────────────────────────────────────────
    race_control: DashboardRaceControlSummary

    # ── Weather ───────────────────────────────────────────────────────────────
    weather: DashboardWeatherSummary | None

    # ── Converter ─────────────────────────────────────────────────────────────

    @classmethod
    def from_summary(cls, summary: SessionDashboardSummary) -> "SessionDashboardResponse":
        """
        Convert a SessionDashboardSummary dataclass (from the service layer)
        into this Pydantic response model.

        This is the only place that knows how to map the service's internal
        structure onto the API's public shape. If the service changes a field
        name or adds a section, update only here.
        """
        return cls(
            session_id=summary.session_id,
            session_name=summary.session_name,
            session_type=summary.session_type,
            race_name=summary.race_name,
            circuit_short_name=summary.circuit_short_name,
            country_name=summary.country_name,
            start_time=summary.start_time,
            is_synced=summary.is_synced,
            has_lap_data=summary.has_lap_data,
            has_stint_data=summary.has_stint_data,
            has_rc_data=summary.has_rc_data,
            has_weather_data=summary.has_weather_data,
            lap_stats=DashboardLapStats(
                total_rows=summary.lap_stats.total_rows,
                driver_count=summary.lap_stats.driver_count,
                max_lap=summary.lap_stats.max_lap,
            ),
            finishing_order=[
                DashboardDriverSummary(
                    position=e.position,
                    driver_number=e.driver_number,
                    driver_name=e.driver_name,
                    max_lap=e.max_lap,
                    laps_behind=e.laps_behind,
                    is_favourite=e.is_favourite,
                )
                for e in summary.finishing_order
            ],
            compound_overview=summary.compound_overview,
            stint_summary=[
                DashboardStintSummary(
                    driver_number=d.driver_number,
                    driver_name=d.driver_name,
                    is_favourite=d.is_favourite,
                    stints=[
                        DashboardStintEntry(
                            stint_number=s.stint_number,
                            compound=s.compound,
                            lap_start=s.lap_start,
                            lap_end=s.lap_end,
                            tyre_age_at_start=s.tyre_age_at_start,
                        )
                        for s in d.stints
                    ],
                )
                for d in summary.stint_summary
            ],
            race_control=DashboardRaceControlSummary(
                key_events=[
                    DashboardKeyEvent(label=ev.label, lap_number=ev.lap_number)
                    for ev in summary.key_rc_events
                ],
                messages=[
                    DashboardRCMessage(
                        lap_number=m.lap_number,
                        flag=m.flag,
                        message=m.message,
                    )
                    for m in summary.rc_messages
                ],
                total=summary.rc_total,
                blue_flag_count=summary.rc_blue_flag_count,
                omitted_count=summary.rc_omitted_count,
            ),
            weather=(
                DashboardWeatherSummary(
                    air_min=summary.weather.air_min,
                    air_max=summary.weather.air_max,
                    track_min=summary.weather.track_min,
                    track_max=summary.weather.track_max,
                    had_rain=summary.weather.had_rain,
                    sample_count=summary.weather.sample_count,
                )
                if summary.weather is not None
                else None
            ),
        )
