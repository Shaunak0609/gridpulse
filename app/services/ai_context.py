import os
from collections import Counter
from datetime import datetime, timezone

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.models.favorite_driver import FavoriteDriver
from app.models.favorite_team import FavoriteTeam
from app.models.lap import Lap
from app.models.notification import Notification
from app.models.race_control_message import RaceControlMessage
from app.models.reminder import Reminder
from app.models.session import Session as RaceSession
from app.models.standing import DriverStanding
from app.models.stint import Stint
from app.models.user import User
from app.models.weather_sample import WeatherSample

SEASON = int(os.getenv("F1_SEASON", "2026"))

# Hard caps — keep context small so it fits comfortably in the AI prompt.
_MAX_STANDINGS = 10
_MAX_SESSIONS = 5
_MAX_REMINDERS = 3
_MAX_NOTIFICATIONS = 3
_MAX_SYNCED_SESSIONS = 3   # most-recent synced sessions to describe
_MAX_RC_MESSAGES = 6       # race control messages per session


def _fmt_time(dt: datetime | None) -> str:
    if not dt:
        return "TBC"
    utc = dt.astimezone(timezone.utc)
    return utc.strftime("%a %d %b %Y, %H:%M UTC")


def _section(title: str, lines: list[str]) -> str:
    body = "\n".join(lines) if lines else "  (none)"
    return f"== {title} ==\n{body}"


# ─── Historical session helpers ───────────────────────────────────────────────

def _weather_summary(session_id: int, db: Session) -> str | None:
    """One-line weather summary, or None if no weather data stored."""
    samples = (
        db.query(WeatherSample)
        .filter(WeatherSample.session_id == session_id)
        .all()
    )
    if not samples:
        return None

    air = [s.air_temperature for s in samples if s.air_temperature is not None]
    track = [s.track_temperature for s in samples if s.track_temperature is not None]
    had_rain = any(s.rainfall for s in samples)

    parts: list[str] = []
    if air:
        parts.append(f"Air {min(air):.1f}–{max(air):.1f} °C")
    if track:
        parts.append(f"Track {min(track):.1f}–{max(track):.1f} °C")
    parts.append("Rain: yes" if had_rain else "Rain: no")
    parts.append(f"({len(samples)} readings)")
    return ", ".join(parts)


def _stint_summary(session_id: int, db: Session) -> str | None:
    """One-line compound usage summary, or None if no stint data stored."""
    stints = (
        db.query(Stint)
        .filter(Stint.session_id == session_id)
        .all()
    )
    if not stints:
        return None

    compounds = Counter(s.compound for s in stints if s.compound)
    if not compounds:
        return f"{len(stints)} stints (compound unknown)"

    breakdown = ", ".join(
        f"{count}×{compound}"
        for compound, count in compounds.most_common()
    )
    return f"{len(stints)} stints — {breakdown}"


def _session_block(session: RaceSession, db: Session) -> list[str]:
    """
    Build a short summary block for one synced session.
    Includes lap count, tyre summary, weather, and recent race control messages.
    Never dumps raw lap rows — only aggregated counts and short text messages.
    """
    lines: list[str] = []

    race_name = session.race.name if session.race else f"Race {session.race_id}"
    location_parts = [
        p for p in [session.circuit_short_name, session.country_name] if p
    ]
    location = f" ({', '.join(location_parts)})" if location_parts else ""
    lines.append(f"  Session : {session.session_name} — {race_name}{location}")
    lines.append(f"  Date    : {_fmt_time(session.start_time)}")

    # Lap count (aggregate only — no individual lap rows)
    lap_count = (
        db.query(func.count(Lap.id))
        .filter(Lap.session_id == session.id)
        .scalar()
    ) or 0
    driver_count = (
        db.query(func.count(distinct(Lap.driver_number)))
        .filter(Lap.session_id == session.id)
        .scalar()
    ) or 0

    if lap_count:
        lines.append(f"  Laps    : {lap_count} stored across {driver_count} drivers")
    else:
        lines.append("  Laps    : none stored (run sync script to ingest)")

    # Tyre / stint summary
    stint_line = _stint_summary(session.id, db)
    if stint_line:
        lines.append(f"  Tyres   : {stint_line}")
    else:
        lines.append("  Tyres   : no stint data stored")

    # Weather summary
    weather_line = _weather_summary(session.id, db)
    if weather_line:
        lines.append(f"  Weather : {weather_line}")
    else:
        lines.append("  Weather : no weather data stored")

    # Race control messages — short text, safe to include verbatim
    rc_all = (
        db.query(RaceControlMessage)
        .filter(RaceControlMessage.session_id == session.id)
        .order_by(RaceControlMessage.date)
        .all()
    )
    if rc_all:
        # Show only the last N to stay within token budget
        shown = rc_all[-_MAX_RC_MESSAGES:]
        omitted = len(rc_all) - len(shown)
        header = f"  Race control ({len(rc_all)} messages"
        header += f", showing last {len(shown)}):" if omitted else "):"
        lines.append(header)
        for msg in shown:
            lap_tag = f"[Lap {msg.lap_number}] " if msg.lap_number is not None else ""
            flag_tag = f"[{msg.flag}] " if msg.flag else ""
            lines.append(f"    {lap_tag}{flag_tag}{msg.message}")
    else:
        lines.append("  Race control : no messages stored")

    return lines


# ─── Main builder ─────────────────────────────────────────────────────────────

def build_context(user: User, db: Session) -> str:
    """
    Gather relevant GridPulse data for the given user and return it as a
    plain-text context string to be injected into the AI prompt.

    Sensitive fields (password_hash, google_sub, auth tokens) are never read.
    Data volumes are capped so the context stays small and focused.
    """
    sections: list[str] = []

    # ── Snapshot timestamp ────────────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    sections.append(_section("GridPulse Data Snapshot", [
        f"  Retrieved : {_fmt_time(now)}",
        "  Note      : This is a database snapshot. GridPulse has no live race feed.",
        "              Do not describe any data in this context as 'live' or 'real-time'.",
    ]))

    # ── User profile ─────────────────────────────────────────────────────────
    display_name = user.username or user.email.split("@")[0]
    sections.append(_section("User", [
        f"  Username : {display_name}",
        f"  Email    : {user.email}",
        f"  Timezone : {user.timezone or 'not set'}",
    ]))

    # ── Favourite drivers ─────────────────────────────────────────────────────
    fav_drivers = (
        db.query(FavoriteDriver)
        .filter(FavoriteDriver.user_id == user.id)
        .all()
    )
    driver_lines = [
        f"  - {fd.driver.full_name} "
        f"(#{fd.driver.driver_number or '?'}, "
        f"{fd.driver.team.name if fd.driver.team else 'no team'})"
        for fd in fav_drivers
    ]
    sections.append(_section("Favourite Drivers", driver_lines))

    # ── Favourite teams ───────────────────────────────────────────────────────
    fav_teams = (
        db.query(FavoriteTeam)
        .filter(FavoriteTeam.user_id == user.id)
        .all()
    )
    team_lines = [f"  - {ft.team.name}" for ft in fav_teams]
    sections.append(_section("Favourite Teams", team_lines))

    # ── Driver standings ──────────────────────────────────────────────────────
    standings = (
        db.query(DriverStanding)
        .filter(DriverStanding.season == SEASON)
        .order_by(DriverStanding.position)
        .limit(_MAX_STANDINGS)
        .all()
    )
    standing_lines = [
        f"  P{s.position}. {s.driver.full_name} — {s.team.name if s.team else '?'} "
        f"— {int(s.points)} pts, {s.wins} wins"
        for s in standings
    ]
    heading = f"Driver Standings ({SEASON}, top {_MAX_STANDINGS})"
    sections.append(_section(heading, standing_lines))

    # ── Upcoming sessions ─────────────────────────────────────────────────────
    upcoming_sessions = (
        db.query(RaceSession)
        .filter(RaceSession.start_time > now)
        .order_by(RaceSession.start_time)
        .limit(_MAX_SESSIONS)
        .all()
    )
    session_lines = [
        f"  - {s.session_name} | {s.race.name} | {_fmt_time(s.start_time)}"
        for s in upcoming_sessions
    ]
    sections.append(_section("Upcoming Sessions", session_lines))

    # ── Upcoming reminders ────────────────────────────────────────────────────
    upcoming_reminders = (
        db.query(Reminder)
        .filter(
            Reminder.user_id == user.id,
            Reminder.reminder_time > now,
        )
        .order_by(Reminder.reminder_time)
        .limit(_MAX_REMINDERS)
        .all()
    )
    reminder_lines = [
        f"  - \"{r.title}\" — {_fmt_time(r.reminder_time)}"
        for r in upcoming_reminders
    ]
    sections.append(_section("Upcoming Reminders", reminder_lines))

    # ── Recent notifications ──────────────────────────────────────────────────
    recent_notifications = (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .limit(_MAX_NOTIFICATIONS)
        .all()
    )
    notif_lines = [
        f"  - {n.title}" + (f": {n.message}" if n.message else "")
        for n in recent_notifications
    ]
    sections.append(_section("Recent Notifications", notif_lines))

    # ── Historical session data ───────────────────────────────────────────────
    # Show summaries for the most recently synced sessions.
    # Individual lap rows are never included — only aggregated counts and
    # short race-control text, so the context stays within token limits.
    synced_sessions = (
        db.query(RaceSession)
        .filter(RaceSession.openf1_session_key.isnot(None))
        .order_by(RaceSession.start_time.desc())
        .limit(_MAX_SYNCED_SESSIONS)
        .all()
    )

    if synced_sessions:
        hist_lines: list[str] = []
        for i, sess in enumerate(synced_sessions):
            hist_lines.extend(_session_block(sess, db))
            if i < len(synced_sessions) - 1:
                hist_lines.append("")   # blank line between sessions
        title = (
            f"Historical Session Data "
            f"(last {len(synced_sessions)} synced, most recent first)"
        )
        sections.append(_section(title, hist_lines))
    else:
        sections.append(_section("Historical Session Data", [
            "  No sessions have been synced from OpenF1 yet.",
            "  Run: python scripts/sync_openf1_session.py --session-key <key>",
        ]))

    # ── Explicit data limitations ─────────────────────────────────────────────
    sections.append(_section("Data NOT Available in GridPulse", [
        "  - Individual race results (finishing positions per race)",
        "  - Qualifying results and grid positions",
        "  - Live race timing of any kind",
        "  - Car telemetry (speed traces, throttle, brake, GPS position)",
        "  - FastF1 positional or sector-level telemetry data",
        "  - Pit stop duration or undercut/overcut analysis",
        "  Note: Lap times, tyre compounds, and weather are stored for synced",
        "        sessions and summarised above — but not all sessions are synced.",
    ]))

    return "\n\n".join(sections)
