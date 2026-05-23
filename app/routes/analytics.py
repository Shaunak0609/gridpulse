from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_optional_user
from app.database.database import get_db
from app.models.user import User
from app.schemas.analytics import (
    DriverComparisonResponse,
    SessionAnalyticsResponse,
    TireAnalyticsSummary,
)
from app.services.analytics_service import (
    build_session_analytics,
    compare_drivers,
    get_session_analytics,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/sessions/{session_id}", response_model=SessionAnalyticsResponse)
def get_session_analytics_endpoint(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """
    Return a full analytics summary for one session.

    Includes:
    - Session-level pace stats (fastest lap, session average)
    - Per-driver lap pace (fastest, average, sector bests)
    - Compound pace averages (derived from laps joined to stint ranges)
    - Per-stint pace breakdown per driver
    - Teammate comparisons (one per team with two drivers present)
    - Race context (safety car and red flag lap numbers)
    - Latest weather reading

    Public endpoint — no token required.
    If a valid Bearer token is provided, the response marks favourite
    drivers with is_favourite=True on driver rows.

    Returns 404 if the session does not exist.
    Returns the full schema with has_lap_data=False (and empty data sections)
    when the session has not been synced or lap data has not been ingested.
    """
    summary = get_session_analytics(session_id, db, current_user)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found.",
        )
    return SessionAnalyticsResponse.from_summary(summary)


@router.get("/sessions/{session_id}/compare", response_model=DriverComparisonResponse)
def compare_session_drivers(
    session_id: int,
    driver1: int = Query(..., description="Car number of the first driver (e.g. 1 for Verstappen)"),
    driver2: int = Query(..., description="Car number of the second driver (e.g. 4 for Norris)"),
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """
    Compare two drivers side-by-side using stored lap and stint data.

    Query parameters:
    - driver1: car number of the first driver
    - driver2: car number of the second driver

    Example: /analytics/sessions/15/compare?driver1=12&driver2=63

    Returns:
    - Both drivers' fastest lap, average lap, lap count, and sector bests
    - fastest_delta and avg_delta in seconds (driver1 - driver2):
        negative value → driver1 is faster
        positive value → driver2 is faster
    - Per-stint average lap time for each driver (with compound label)

    Public endpoint — no token required.
    If a valid Bearer token is provided, is_favourite is set on both driver
    summary objects.

    Returns 404 if:
    - The session does not exist
    - The session has no synced lap data
    - Either driver number is not present in the session's lap data
    """
    # Step 1 — confirm the session exists
    summary = get_session_analytics(session_id, db, current_user)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found.",
        )

    # Step 2 — require lap data (cannot compare without it)
    if not summary.has_lap_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No lap data has been synced for session {session_id}. "
                   f"Run the OpenF1 sync script first.",
        )

    # Step 3 — perform the comparison
    comparison = compare_drivers(summary, driver1, driver2)
    if comparison is None:
        # Tell the caller which driver numbers are actually in the data.
        available = sorted(dp.driver_number for dp in summary.driver_pace)
        available_str = ", ".join(f"#{n}" for n in available)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"One or both driver numbers (#{driver1}, #{driver2}) were not found "
                f"in session {session_id} lap data. "
                f"Drivers with lap data in this session: {available_str}."
            ),
        )

    return DriverComparisonResponse.from_comparison(comparison)


@router.get("/sessions/{session_id}/tires", response_model=TireAnalyticsSummary)
def get_session_tire_analytics(
    session_id: int,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """
    Return tyre and stint pace analytics for one session.

    A focused subset of the full analytics response — useful when the frontend
    only needs compound pace data without loading the full driver pace table.

    Returns:
    - compound_pace: average and fastest lap time per compound, derived by
      joining laps to their stint's lap range. Empty list if stints lack
      lap ranges (has_compound_pace will be False).
    - stint_pace: average lap time per driver per stint. Empty list if no
      stint or lap data is synced.
    - has_compound_pace: False when the lap-to-stint join is not possible
      (stints present but lap_start / lap_end values are missing).

    Public endpoint — no token required.
    If a valid Bearer token is provided, is_favourite is set on stint_pace rows.

    Returns 404 if the session does not exist.
    Returns an empty TireAnalyticsSummary (all lists empty, has_compound_pace
    False) when the session has no synced lap or stint data.
    """
    summary = get_session_analytics(session_id, db, current_user)
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found.",
        )

    # Convert only the tyre section — avoids sending unused driver/teammate data.
    from app.schemas.analytics import (
        AnalyticsStintEntry,
        CompoundUsageSummary,
    )

    return TireAnalyticsSummary(
        has_compound_pace=summary.has_compound_pace,
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
        stint_pace=[
            AnalyticsStintEntry(
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
            for e in summary.stint_pace
        ],
    )
