"""
strategy_dashboard.py (schemas)

Pydantic response models for the GET /sessions/{id}/strategy endpoint.

These schemas sit between the strategy_dashboard service (which returns
Python dataclasses) and the HTTP response (which must be JSON).

Design rules:
  - Every field is either a primitive or a nested schema — no raw ORM rows.
  - Sensitive fields (user email, auth tokens) are never included.
  - No ML prediction fields, no track map fields.
  - has_* flags are always present so the frontend can render empty states
    without checking list lengths.
  - Field names match the dataclass names in strategy_dashboard.py so the
    from_summary() converter stays small.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.services.strategy_dashboard import StrategyDashboardSummary


# ─── Nested schemas (smallest → largest) ─────────────────────────────────────

class StrategyCompoundUsage(BaseModel):
    """Aggregate usage stats for one tyre compound across all drivers."""
    compound: str             # SOFT / MEDIUM / HARD / INTERMEDIATE / WET
    stint_count: int          # total stints on this compound
    driver_count: int         # distinct drivers who used it
    avg_stint_laps: float | None   # average stint length; None if lap ranges unavailable


class StrategyStintSummary(BaseModel):
    """One stint within a driver's race strategy."""
    stint_number: int | None
    compound: str | None      # SOFT / MEDIUM / HARD / INTERMEDIATE / WET
    lap_start: int | None
    lap_end: int | None
    tyre_age_at_start: int | None   # 0 = new tyre; >0 = pre-used laps at start
    stint_laps: int | None    # lap_end - lap_start + 1; None if either bound missing


class StrategyDriverSummary(BaseModel):
    """All strategy data for one driver."""
    driver_number: int
    driver_name: str
    stop_count: int                   # pit stops made = len(stints) - 1
    compound_sequence: list[str]      # ordered compound names, e.g. ["MEDIUM", "HARD"]
    stints: list[StrategyStintSummary]
    longest_stint_laps: int | None    # laps on the longest single stint
    is_favourite: bool


class StrategyPitWindow(BaseModel):
    """
    A cluster of pit stops happening around the same lap range.
    Derived by grouping pit laps within 6 laps of each other.
    """
    window_number: int   # 1-based
    lap_min: int         # earliest pit lap in this cluster
    lap_max: int         # latest pit lap in this cluster
    driver_count: int    # how many drivers pitted in this window


class StrategyRCEvent(BaseModel):
    """One strategy-relevant race control message (blue-flag messages excluded)."""
    lap_number: int | None
    flag: str | None     # e.g. "YELLOW", "DOUBLE YELLOW", "RED", "SAFETY CAR"
    message: str


class StrategyRaceControlContext(BaseModel):
    """
    Strategy-relevant race control events only.

    Filtered to safety cars, VSC, red flags, pit lane status, weather warnings,
    retirements, and flag conditions that affect strategy decisions.
    Blue-flag (lapping) messages are always excluded.
    """
    events: list[StrategyRCEvent]
    total_strategy_events: int   # number of events returned (capped at 25)


class StrategyWeatherContext(BaseModel):
    """
    Weather conditions that influenced strategy decisions.

    wet_tyre_drivers: drivers who ran INTERMEDIATE or WET tyres — the clearest
    indicator that conditions forced a strategy change.
    latest_* fields: values from the most recent weather sample in the session.
    """
    had_rain: bool
    wet_tyre_drivers: list[str]   # driver names who used INTERMEDIATE or WET
    air_min: float | None         # °C, session minimum
    air_max: float | None         # °C, session maximum
    track_min: float | None       # °C, session minimum
    track_max: float | None       # °C, session maximum
    sample_count: int
    latest_air_temp: float | None    # °C at the latest recorded sample
    latest_track_temp: float | None  # °C at the latest recorded sample
    latest_rainfall: bool | None     # whether it was raining at the latest sample


# ─── Top-level response ───────────────────────────────────────────────────────

class StrategyDashboardResponse(BaseModel):
    """
    Full strategy dashboard payload for one session.

    Returned by GET /sessions/{id}/strategy.
    Every data section has a has_* flag — callers should check these before
    rendering cards so they can show appropriate empty states.

    stop_count_groups maps stop count → list of driver names, e.g.:
      {"1": ["Verstappen", "Norris"], "2": ["Hamilton"]}
    JSON keys are always strings even though the underlying values are integers.
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
    has_stint_data: bool
    has_lap_data: bool
    has_rc_data: bool
    has_weather_data: bool

    # ── Compound overview ─────────────────────────────────────────────────────
    compound_usage: list[StrategyCompoundUsage]

    # ── Per-driver strategies ─────────────────────────────────────────────────
    driver_strategies: list[StrategyDriverSummary]

    # ── Stop-count grouping ───────────────────────────────────────────────────
    # e.g. {1: ["Verstappen", "Norris"], 2: ["Hamilton"]}
    stop_count_groups: dict[int, list[str]]

    # ── Pit windows ───────────────────────────────────────────────────────────
    pit_windows: list[StrategyPitWindow]

    # ── Strategy-relevant race control ────────────────────────────────────────
    race_control: StrategyRaceControlContext

    # ── Weather ───────────────────────────────────────────────────────────────
    weather: StrategyWeatherContext | None

    # ── Rule-based insights ───────────────────────────────────────────────────
    # Plain-English sentences derived from stored data — no ML, no predictions.
    insights: list[str]

    # ── Converter ─────────────────────────────────────────────────────────────

    @classmethod
    def from_summary(cls, summary: StrategyDashboardSummary) -> "StrategyDashboardResponse":
        """
        Convert a StrategyDashboardSummary dataclass (from the service layer)
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
            has_stint_data=summary.has_stint_data,
            has_lap_data=summary.has_lap_data,
            has_rc_data=summary.has_rc_data,
            has_weather_data=summary.has_weather_data,
            compound_usage=[
                StrategyCompoundUsage(
                    compound=cu.compound,
                    stint_count=cu.stint_count,
                    driver_count=cu.driver_count,
                    avg_stint_laps=cu.avg_stint_laps,
                )
                for cu in summary.compound_usage
            ],
            driver_strategies=[
                StrategyDriverSummary(
                    driver_number=ds.driver_number,
                    driver_name=ds.driver_name,
                    stop_count=ds.stop_count,
                    compound_sequence=ds.compound_sequence,
                    longest_stint_laps=ds.longest_stint_laps,
                    is_favourite=ds.is_favourite,
                    stints=[
                        StrategyStintSummary(
                            stint_number=s.stint_number,
                            compound=s.compound,
                            lap_start=s.lap_start,
                            lap_end=s.lap_end,
                            tyre_age_at_start=s.tyre_age_at_start,
                            stint_laps=s.stint_laps,
                        )
                        for s in ds.stints
                    ],
                )
                for ds in summary.driver_strategies
            ],
            stop_count_groups=summary.stop_count_groups,
            pit_windows=[
                StrategyPitWindow(
                    window_number=pw.window_number,
                    lap_min=pw.lap_min,
                    lap_max=pw.lap_max,
                    driver_count=pw.driver_count,
                )
                for pw in summary.pit_windows
            ],
            race_control=StrategyRaceControlContext(
                events=[
                    StrategyRCEvent(
                        lap_number=ev.lap_number,
                        flag=ev.flag,
                        message=ev.message,
                    )
                    for ev in summary.strategy_rc_events
                ],
                total_strategy_events=len(summary.strategy_rc_events),
            ),
            weather=(
                StrategyWeatherContext(
                    had_rain=summary.weather_context.had_rain,
                    wet_tyre_drivers=summary.weather_context.wet_tyre_drivers,
                    air_min=summary.weather_context.air_min,
                    air_max=summary.weather_context.air_max,
                    track_min=summary.weather_context.track_min,
                    track_max=summary.weather_context.track_max,
                    sample_count=summary.weather_context.sample_count,
                    latest_air_temp=summary.weather_context.latest_air_temp,
                    latest_track_temp=summary.weather_context.latest_track_temp,
                    latest_rainfall=summary.weather_context.latest_rainfall,
                )
                if summary.weather_context is not None
                else None
            ),
            insights=summary.insights,
        )
