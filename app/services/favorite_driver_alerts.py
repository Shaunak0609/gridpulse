"""
Generates session-level in-app alerts (and optional emails) for users whose
favourite drivers appear in a synced OpenF1 session.

Four alert types are supported, each grounded in a specific database table:

  favorite_driver_fastest_lap
      The favourite driver set the session's fastest stored lap time.
      Source: laps table — MIN(lap_duration) with pit-out laps excluded.

  favorite_driver_strategy
      Stint data exists for the driver. Summarises compounds used, stop count,
      and longest stint when lap ranges are stored.
      Source: stints table — all rows for this driver in this session.

  favorite_driver_rc_mention
      Race control issued at least one message targeting this driver's car
      number via the structured driver_number column. No text search is used —
      text matching is too unreliable across OpenF1 message formats.
      Source: race_control_messages — rows where driver_number matches.

  favorite_driver_lap_comparison
      For race and sprint sessions only: the driver completed significantly
      fewer laps than the session maximum (gap of 4 or more). The alert uses
      cautious language and explicitly states GridPulse cannot confirm the
      reason — official retirement and classification data is not stored.
      Source: laps table — MAX(lap_number) per driver vs session-wide MAX.

Dedup
-----
One notification per (user_id, type, related_driver_id, related_session_id).
Running generate_session_alerts() more than once for the same session is safe —
duplicate alerts are counted as skipped, not duplicated.

Email
-----
Sent after the notification row is committed so in-app delivery is never lost
even if the email call fails. Requires both email_notifications_enabled and
favorite_driver_email_alerts_enabled to be true on the user.

What is intentionally not included
-----------------------------------
- Position gains/losses — the laps table has no per-lap position column.
- Retirement confirmation — no race_results table exists; only lap count
  comparison is possible, with cautious wording.
- Pit stop durations — not stored; stint transitions give approximate windows.
- Penalty detection via text search — message text is inconsistent across
  sessions; only the structured driver_number column is reliable.
- Any live or real-time data — all data is from stored OpenF1 historical snapshots.
"""

from sqlalchemy import func
from sqlalchemy.orm import Session as DBSession

from app.models.favorite_driver import FavoriteDriver
from app.models.lap import Lap
from app.models.notification import Notification
from app.models.race_control_message import RaceControlMessage
from app.models.session import Session as RaceSession
from app.models.stint import Stint
from app.services.email_service import send_email

_LAP_COMPARISON_MIN_GAP = 4  # only alert when driver is ≥4 laps short of max
_RACE_SESSION_TYPES = {"race", "sprint"}

_ALL_ALERT_TYPES = [
    "favorite_driver_fastest_lap",
    "favorite_driver_strategy",
    "favorite_driver_rc_mention",
    "favorite_driver_lap_comparison",
]


# ── formatting helpers ────────────────────────────────────────────────────────

def _fmt_lap(seconds: float) -> str:
    """Format seconds as M:SS.mmm — e.g. 88.456 → '1:28.456'."""
    m = int(seconds // 60)
    s = seconds - m * 60
    return f"{m}:{s:06.3f}"


def _session_label(session: RaceSession) -> str:
    """Return a readable label like 'Australian Grand Prix Race'."""
    race_name = session.race.name if session.race else "Unknown Race"
    return f"{race_name} {session.session_name}"


def _email_body(user, notification_message: str) -> str:
    username = user.username or user.email
    return (
        f"Hi {username},\n\n"
        f"{notification_message}\n\n"
        f"All GridPulse alerts are derived from stored OpenF1 historical data, "
        f"not live timing. Lap times and strategy data are approximate.\n\n"
        f"— The GridPulse team\n\n"
        f"To stop receiving these emails, turn off favourite-driver email alerts "
        f"in your GridPulse settings."
    )


# ── shared notification creator ───────────────────────────────────────────────

def _maybe_notify(
    *,
    user,
    driver,
    session: RaceSession,
    alert_type: str,
    title: str,
    message: str,
    email_subject: str,
    db: DBSession,
    counts: dict,
) -> None:
    """
    Create one notification for (user, alert_type, driver, session) if none
    exists yet. Commit first, then attempt email. Updates counts in-place.
    """
    already_exists = (
        db.query(Notification)
        .filter_by(
            user_id=user.id,
            type=alert_type,
            related_driver_id=driver.id,
            related_session_id=session.id,
        )
        .first()
        is not None
    )
    if already_exists:
        counts["skipped"] += 1
        return

    db.add(Notification(
        user_id=user.id,
        type=alert_type,
        title=title,
        message=message,
        related_driver_id=driver.id,
        related_race_id=session.race_id,
        related_session_id=session.id,
    ))
    db.commit()
    counts["created"] += 1

    if user.email_notifications_enabled and user.favorite_driver_email_alerts_enabled:
        try:
            send_email(
                to=user.email,
                subject=email_subject,
                body=_email_body(user, message),
            )
            counts["emails_sent"] += 1
        except RuntimeError:
            counts["emails_failed"] += 1


# ── alert detectors ───────────────────────────────────────────────────────────

def _detect_fastest_lap(
    session: RaceSession, driver, user, db: DBSession, alert_counts: dict
) -> None:
    """Alert if this driver holds the session fastest stored lap."""
    session_best: float | None = (
        db.query(func.min(Lap.lap_duration))
        .filter(
            Lap.session_id == session.id,
            Lap.is_pit_out_lap == False,
            Lap.lap_duration.isnot(None),
        )
        .scalar()
    )
    if session_best is None:
        return

    driver_best: float | None = (
        db.query(func.min(Lap.lap_duration))
        .filter(
            Lap.session_id == session.id,
            Lap.driver_number == driver.driver_number,
            Lap.is_pit_out_lap == False,
            Lap.lap_duration.isnot(None),
        )
        .scalar()
    )
    if driver_best is None:
        return

    # Small tolerance to handle floating-point representation differences.
    if abs(driver_best - session_best) > 0.001:
        return

    label = _session_label(session)
    msg = (
        f"{driver.full_name} set the session fastest stored lap of "
        f"{_fmt_lap(driver_best)} in the {label}. "
        f"Derived from stored OpenF1 lap data — not the official fastest lap award."
    )
    _maybe_notify(
        user=user,
        driver=driver,
        session=session,
        alert_type="favorite_driver_fastest_lap",
        title="Fastest lap in session",
        message=msg,
        email_subject=f"GridPulse: {driver.full_name} — fastest lap in {label}",
        db=db,
        counts=alert_counts["favorite_driver_fastest_lap"],
    )


def _detect_strategy(
    session: RaceSession, driver, user, db: DBSession, alert_counts: dict
) -> None:
    """Alert summarising the driver's tyre strategy when stint data exists."""
    stints = (
        db.query(Stint)
        .filter(
            Stint.session_id == session.id,
            Stint.driver_number == driver.driver_number,
        )
        .order_by(Stint.stint_number)
        .all()
    )
    if not stints:
        return

    compounds = [s.compound or "UNKNOWN" for s in stints]
    sequence = " → ".join(compounds)
    stop_count = max(len(stints) - 1, 0)
    stop_word = "pit stop" if stop_count == 1 else "pit stops"

    # Longest stint note — only when lap_start and lap_end are both stored.
    stints_with_range = [
        s for s in stints
        if s.lap_start is not None and s.lap_end is not None
    ]
    longest_note = ""
    if stints_with_range:
        longest = max(stints_with_range, key=lambda s: s.lap_end - s.lap_start)
        laps = longest.lap_end - longest.lap_start + 1
        compound_str = longest.compound or "unknown compound"
        longest_note = f" Longest stint: {laps} laps on {compound_str}."

    label = _session_label(session)
    msg = (
        f"{driver.full_name}'s tyre strategy in the {label}: "
        f"{sequence} ({stop_count} {stop_word}).{longest_note} "
        f"Derived from stored OpenF1 stint records — pit windows are approximate."
    )
    _maybe_notify(
        user=user,
        driver=driver,
        session=session,
        alert_type="favorite_driver_strategy",
        title="Strategy summary",
        message=msg,
        email_subject=f"GridPulse: {driver.full_name} — strategy summary for {label}",
        db=db,
        counts=alert_counts["favorite_driver_strategy"],
    )


def _detect_rc_mention(
    session: RaceSession, driver, user, db: DBSession, alert_counts: dict
) -> None:
    """
    Alert if race control issued messages targeting this driver's car number.
    Only the structured driver_number column is used — no text search.
    """
    messages = (
        db.query(RaceControlMessage)
        .filter(
            RaceControlMessage.session_id == session.id,
            RaceControlMessage.driver_number == driver.driver_number,
        )
        .order_by(RaceControlMessage.date)
        .all()
    )
    if not messages:
        return

    label = _session_label(session)
    count = len(messages)

    if count == 1:
        rc = messages[0]
        lap_note = f" (lap {rc.lap_number})" if rc.lap_number else ""
        msg = (
            f"{driver.full_name} was mentioned in a race control message "
            f"during the {label}{lap_note}: \"{rc.message}\"."
        )
    else:
        last = messages[-1]
        lap_note = f" (lap {last.lap_number})" if last.lap_number else ""
        msg = (
            f"{driver.full_name} was mentioned in {count} race control "
            f"messages during the {label}. "
            f"Most recent{lap_note}: \"{last.message}\"."
        )

    _maybe_notify(
        user=user,
        driver=driver,
        session=session,
        alert_type="favorite_driver_rc_mention",
        title="Race control mention",
        message=msg,
        email_subject=f"GridPulse: {driver.full_name} — race control mention in {label}",
        db=db,
        counts=alert_counts["favorite_driver_rc_mention"],
    )


def _detect_lap_comparison(
    session: RaceSession, driver, user, db: DBSession, alert_counts: dict
) -> None:
    """
    For race/sprint sessions: alert if the driver completed notably fewer laps
    than the session maximum. Uses cautious language — GridPulse has no
    official retirement or classification data.
    """
    if session.session_type not in _RACE_SESSION_TYPES:
        return

    session_max: int | None = (
        db.query(func.max(Lap.lap_number))
        .filter(Lap.session_id == session.id)
        .scalar()
    )
    if session_max is None:
        return

    driver_max: int | None = (
        db.query(func.max(Lap.lap_number))
        .filter(
            Lap.session_id == session.id,
            Lap.driver_number == driver.driver_number,
        )
        .scalar()
    )
    if driver_max is None:
        return

    if session_max - driver_max < _LAP_COMPARISON_MIN_GAP:
        return

    label = _session_label(session)
    msg = (
        f"GridPulse's synced data shows {driver.full_name} completed "
        f"{driver_max} laps in the {label}, compared to a session maximum "
        f"of {session_max}. GridPulse cannot confirm the reason — official "
        f"retirement and classification data is not stored."
    )
    _maybe_notify(
        user=user,
        driver=driver,
        session=session,
        alert_type="favorite_driver_lap_comparison",
        title="Lap data note",
        message=msg,
        email_subject=f"GridPulse: {driver.full_name} — lap data note for {label}",
        db=db,
        counts=alert_counts["favorite_driver_lap_comparison"],
    )


# ── entry point ───────────────────────────────────────────────────────────────

def generate_session_alerts(session_id: int, db: DBSession) -> dict:
    """
    Detect and create favourite-driver alerts for a specific session.

    Loads the session, identifies which favourite drivers have data in it,
    runs each detector in turn, and returns a summary of what was created or
    skipped. Safe to call more than once — duplicate alerts are skipped, not
    duplicated.

    Returns a dict with per-alert-type counts and overall totals. If the
    session does not exist or has not been synced, returns an error/status dict
    with no notifications created.
    """
    session = db.query(RaceSession).filter(RaceSession.id == session_id).first()
    if session is None:
        return {"error": f"Session {session_id} not found."}

    if session.openf1_session_key is None:
        return {
            "session_id": session_id,
            "session_name": getattr(session, "session_name", "Unknown"),
            "is_synced": False,
            "message": (
                "Session has not been linked to an OpenF1 session key. "
                "Run sync_openf1_session.py --session-key <key> first."
            ),
        }

    # Build per-type count buckets.
    alert_counts = {
        t: {"created": 0, "skipped": 0, "emails_sent": 0, "emails_failed": 0}
        for t in _ALL_ALERT_TYPES
    }

    # Collect every car number that actually appears in this session's data so
    # we skip the detectors entirely for drivers with no rows at all.
    car_numbers_in_session: set[int] = set()

    for (num,) in (
        db.query(Lap.driver_number)
        .filter(Lap.session_id == session_id)
        .distinct()
    ):
        car_numbers_in_session.add(num)

    for (num,) in (
        db.query(Stint.driver_number)
        .filter(Stint.session_id == session_id)
        .distinct()
    ):
        car_numbers_in_session.add(num)

    for (num,) in (
        db.query(RaceControlMessage.driver_number)
        .filter(
            RaceControlMessage.session_id == session_id,
            RaceControlMessage.driver_number.isnot(None),
        )
        .distinct()
    ):
        car_numbers_in_session.add(num)

    favorites = db.query(FavoriteDriver).all()
    drivers_checked = 0

    for fav in favorites:
        user = fav.user
        driver = fav.driver

        # Respect the user's in-app notification opt-out.
        if not user.favorite_driver_notifications_enabled:
            continue

        # Skip drivers with no car number or no data in this session.
        if driver.driver_number is None:
            continue
        if driver.driver_number not in car_numbers_in_session:
            continue

        drivers_checked += 1

        _detect_fastest_lap(session, driver, user, db, alert_counts)
        _detect_strategy(session, driver, user, db, alert_counts)
        _detect_rc_mention(session, driver, user, db, alert_counts)
        _detect_lap_comparison(session, driver, user, db, alert_counts)

    total_created = sum(v["created"] for v in alert_counts.values())
    total_skipped = sum(v["skipped"] for v in alert_counts.values())
    total_emails_sent = sum(v["emails_sent"] for v in alert_counts.values())
    total_emails_failed = sum(v["emails_failed"] for v in alert_counts.values())

    return {
        "session_id": session_id,
        "session_name": session.session_name,
        "race_name": session.race.name if session.race else None,
        "is_synced": True,
        "favorite_drivers_checked": drivers_checked,
        "alerts": alert_counts,
        "total_created": total_created,
        "total_skipped": total_skipped,
        "emails_sent": total_emails_sent,
        "emails_failed": total_emails_failed,
    }
