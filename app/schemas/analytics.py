"""
analytics.py (schemas)

Pydantic response models for the GET /sessions/{id}/analytics endpoint.

These schemas sit between the analytics_service (which returns Python dataclasses)
and the HTTP response (which must be JSON-serialisable).

Design rules:
  - Every field is either a primitive or a nested schema — no raw ORM rows.
  - Sensitive fields (user email, auth tokens, user IDs) are never included.
  - No ML prediction fields, no track map fields.
  - has_* flags are always present so the frontend can render empty states
    without inspecting list lengths.
  - Lap times are floats in seconds — frontend converts to M:SS.mmm if needed.
  - Delta values follow the sign convention (driver_a - driver_b):
      negative → driver A is faster
      positive → driver B is faster
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.services.analytics_service import SessionAnalyticsSummary


# ─── Nested schemas (smallest → largest) ─────────────────────────────────────

class DriverAnalyticsSummary(BaseModel):
    """
    Lap pace data for one driver in a session.

    fastest_lap and average_lap are in seconds with millisecond precision.
    average_lap is None when the driver has fewer than 3 timed laps —
    a single-lap or two-lap average is too small a sample to be meaningful.
    best_s1/s2/s3 are the minimum recorded sector times across all laps
    (not just timed laps — sectors can be valid when the overall lap is not).
    """
    driver_number: int
    driver_name: str
    lap_count: int             # total lap rows stored for this driver
    timed_lap_count: int       # laps with a valid lap_duration (pit-out excluded)
    fastest_lap: float | None  # seconds; None if no valid timed laps
    average_lap: float | None  # seconds; None if fewer than 3 timed laps
    best_s1: float | None
    best_s2: float | None
    best_s3: float | None
    is_favourite: bool


class CompoundUsageSummary(BaseModel):
    """
    Average lap pace on one tyre compound, derived by joining lap times to
    the stint records that cover those laps.

    sample_lap_count shows how many laps contributed — a low number (< 10)
    means the average may not be representative.
    """
    compound: str              # SOFT / MEDIUM / HARD / INTERMEDIATE / WET
    avg_lap_time: float | None    # seconds; mean of all timed laps on this compound
    fastest_lap_time: float | None  # quickest single lap recorded on this compound
    driver_count: int          # distinct drivers who contributed laps
    sample_lap_count: int      # number of laps that formed the average


class AnalyticsStintEntry(BaseModel):
    """
    Average pace for one driver on one specific stint, derived by averaging
    timed laps within the stint's lap_start–lap_end range.

    avg_lap_time is None when fewer than 3 timed laps fall within the range.
    """
    driver_number: int
    driver_name: str
    stint_number: int | None
    compound: str | None
    lap_start: int | None
    lap_end: int | None
    avg_lap_time: float | None   # seconds; None if too few laps in this range
    laps_counted: int            # valid timed laps that formed the average
    is_favourite: bool


class TireAnalyticsSummary(BaseModel):
    """
    All tyre-related analytics for a session.

    compound_pace: average pace per compound (requires laps joined to stints).
    stint_pace: per-driver, per-stint pace breakdown.
    has_compound_pace: False when stint lap ranges are unavailable, making the
    compound join impossible even if stint data exists.
    """
    compound_pace: list[CompoundUsageSummary]
    stint_pace: list[AnalyticsStintEntry]
    has_compound_pace: bool


class TeammateComparisonSummary(BaseModel):
    """
    Pace delta between two teammates for a session.

    fastest_delta and avg_delta are (driver_a - driver_b) in seconds.
    A negative value means driver A is faster; positive means driver B is faster.
    None when either driver lacks enough data to compute a meaningful figure.
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


class AnalyticsRaceContext(BaseModel):
    """
    Race control events that affect pace interpretation.

    safety_car_laps and red_flag_laps contain the lap numbers where those
    events occurred. Lap times recorded on those laps are not representative
    of true race pace — the frontend and AI should flag this when displaying
    or discussing those laps.
    """
    rc_total: int
    safety_car_laps: list[int]
    red_flag_laps: list[int]


class AnalyticsWeatherSummary(BaseModel):
    """
    The most recent weather reading for the session.

    Provides context for pace interpretation — e.g., high track temperature
    may accelerate tyre degradation; rainfall (True) means wet conditions.
    """
    air_temperature: float | None   # degrees Celsius
    track_temperature: float | None
    humidity: float | None          # percentage 0–100
    rainfall: bool | None           # True = raining at the latest reading
    wind_speed: float | None        # metres per second


class DriverComparisonResponse(BaseModel):
    """
    Side-by-side analytics for two specific drivers within a session.

    Used when the frontend needs a focused comparison between two drivers
    (e.g. selected from a dropdown). Produced by compare_drivers() in the
    analytics service and converted here by from_comparison().

    fastest_delta / avg_delta follow the same sign convention as
    TeammateComparisonSummary: (driver_a - driver_b), negative = A faster.
    """
    driver_a: DriverAnalyticsSummary
    driver_b: DriverAnalyticsSummary
    fastest_delta: float | None
    avg_delta: float | None
    driver_a_stints: list[AnalyticsStintEntry]
    driver_b_stints: list[AnalyticsStintEntry]

    @classmethod
    def from_comparison(cls, comp: object) -> "DriverComparisonResponse":
        """
        Convert a DriverComparison dataclass from the analytics service into
        this Pydantic response model.
        """
        return cls(
            driver_a=_driver_schema(comp.driver_a),
            driver_b=_driver_schema(comp.driver_b),
            fastest_delta=comp.fastest_delta,
            avg_delta=comp.avg_delta,
            driver_a_stints=[_stint_schema(e) for e in comp.driver_a_stints],
            driver_b_stints=[_stint_schema(e) for e in comp.driver_b_stints],
        )


# ─── Top-level response ───────────────────────────────────────────────────────

class SessionAnalyticsResponse(BaseModel):
    """
    Full analytics payload for one session.

    Returned by GET /sessions/{id}/analytics.

    All data is derived from stored laps, stints, race control messages, and
    weather samples — never invented. Callers must check has_* flags before
    rendering sections; lists are empty (not absent) when data is unavailable.

    Lap times are in seconds as floats. The frontend formats these for display
    (e.g. converting 92.432 to "1:32.432").

    data_note is a plain-English explanation of any data gaps that limit the
    analytics — None when data is complete.
    """

    # ── Identity ──────────────────────────────────────────────────────────────
    session_id: int
    session_name: str
    session_type: str            # "race", "sprint", "qualifying", "fp1", …
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
    has_compound_pace: bool      # False when stint lap ranges are missing

    # ── Session-level pace stats ──────────────────────────────────────────────
    session_fastest_lap: float | None    # best single lap across all drivers (seconds)
    session_fastest_driver: str | None   # name of the driver who set the fastest lap
    session_avg_lap: float | None        # mean of all timed laps in the session

    # ── Per-driver pace ───────────────────────────────────────────────────────
    # Sorted fastest first; drivers with no timed laps appear at the end.
    driver_pace: list[DriverAnalyticsSummary]

    # ── Tyre analytics (compound pace + per-stint breakdown) ──────────────────
    tire_analytics: TireAnalyticsSummary

    # ── Teammate comparisons ──────────────────────────────────────────────────
    # One entry per team with exactly two drivers present in the session.
    # Sorted by absolute fastest_delta (closest battle first).
    teammate_comparisons: list[TeammateComparisonSummary]

    # ── Race control context ──────────────────────────────────────────────────
    race_context: AnalyticsRaceContext

    # ── Weather (latest reading) ──────────────────────────────────────────────
    weather: AnalyticsWeatherSummary | None

    # ── Data quality note ─────────────────────────────────────────────────────
    data_note: str | None

    # ── Converter ─────────────────────────────────────────────────────────────

    @classmethod
    def from_summary(cls, summary: SessionAnalyticsSummary) -> "SessionAnalyticsResponse":
        """
        Convert a SessionAnalyticsSummary dataclass (from the analytics service)
        into this Pydantic response model.

        This is the only place that knows how to map the service's internal
        structure onto the API's public shape. If the service adds a new field,
        update only here.
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
            has_compound_pace=summary.has_compound_pace,
            session_fastest_lap=summary.session_fastest_lap,
            session_fastest_driver=summary.session_fastest_driver,
            session_avg_lap=summary.session_avg_lap,
            driver_pace=[_driver_schema(dp) for dp in summary.driver_pace],
            tire_analytics=TireAnalyticsSummary(
                compound_pace=[
                    CompoundUsageSummary(
                        compound=cp.compound,
                        avg_lap_time=cp.avg_lap_time,
                        fastest_lap_time=cp.fastest_lap_time,
                        driver_count=cp.driver_count,
                        sample_lap_count=cp.sample_lap_count,
                    )
                    for cp in summary.compound_pace
                ],
                stint_pace=[_stint_schema(e) for e in summary.stint_pace],
                has_compound_pace=summary.has_compound_pace,
            ),
            teammate_comparisons=[
                TeammateComparisonSummary(
                    team_name=tc.team_name,
                    driver_a_number=tc.driver_a_number,
                    driver_a_name=tc.driver_a_name,
                    driver_a_fastest=tc.driver_a_fastest,
                    driver_a_avg=tc.driver_a_avg,
                    driver_b_number=tc.driver_b_number,
                    driver_b_name=tc.driver_b_name,
                    driver_b_fastest=tc.driver_b_fastest,
                    driver_b_avg=tc.driver_b_avg,
                    fastest_delta=tc.fastest_delta,
                    avg_delta=tc.avg_delta,
                )
                for tc in summary.teammate_comparisons
            ],
            race_context=AnalyticsRaceContext(
                rc_total=summary.rc_total,
                safety_car_laps=summary.safety_car_laps,
                red_flag_laps=summary.red_flag_laps,
            ),
            weather=(
                AnalyticsWeatherSummary(
                    air_temperature=summary.latest_weather.air_temperature,
                    track_temperature=summary.latest_weather.track_temperature,
                    humidity=summary.latest_weather.humidity,
                    rainfall=summary.latest_weather.rainfall,
                    wind_speed=summary.latest_weather.wind_speed,
                )
                if summary.latest_weather is not None
                else None
            ),
            data_note=summary.data_note,
        )


# ─── Private converters (used by from_summary and from_comparison) ────────────

def _driver_schema(dp: object) -> DriverAnalyticsSummary:
    return DriverAnalyticsSummary(
        driver_number=dp.driver_number,
        driver_name=dp.driver_name,
        lap_count=dp.lap_count,
        timed_lap_count=dp.timed_lap_count,
        fastest_lap=dp.fastest_lap,
        average_lap=dp.average_lap,
        best_s1=dp.best_s1,
        best_s2=dp.best_s2,
        best_s3=dp.best_s3,
        is_favourite=dp.is_favourite,
    )


def _stint_schema(e: object) -> AnalyticsStintEntry:
    return AnalyticsStintEntry(
        driver_number=e.driver_number,
        driver_name=e.driver_name,
        stint_number=e.stint_number,
        compound=e.compound,
        lap_start=e.lap_start,
        lap_end=e.lap_end,
        avg_lap_time=e.avg_lap_time,
        laps_counted=e.laps_counted,
        is_favourite=e.is_favourite,
    )
