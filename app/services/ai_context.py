import os
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.driver import Driver
from app.models.favorite_driver import FavoriteDriver
from app.models.favorite_team import FavoriteTeam
from app.models.lap import Lap
from app.models.notification import Notification
from app.models.reminder import Reminder
from app.models.session import Session as RaceSession
from app.models.standing import DriverStanding
from app.models.user import User
from app.services.session_dashboard import build_session_summary

SEASON = int(os.getenv("F1_SEASON", "2026"))

# Context budget caps — keep total prompt tokens well under the Groq free-tier
# TPM limit for llama-3.1-8b-instant (6 000 TPM).
_MAX_STANDINGS = 10
_MAX_SESSIONS = 5
_MAX_REMINDERS = 3
_MAX_NOTIFICATIONS = 3
_MAX_SYNCED_SESSIONS = 2    # most-recent synced sessions to describe

# AI-specific caps — tighter than the service-level caps to protect the
# Groq free-tier 6 000 TPM limit. The session dashboard endpoint uses
# higher caps because it doesn't need to fit inside a single prompt.
_AI_MAX_RC = 15             # RC messages per session (service cap is 40)
_AI_MAX_DRIVER_LAPS = 10    # per-driver lap rows for qualifying/FP sessions


def _fmt_time(dt: datetime | None) -> str:
    if not dt:
        return "TBC"
    utc = dt.astimezone(timezone.utc)
    return utc.strftime("%a %d %b %Y, %H:%M UTC")


def _section(title: str, lines: list[str]) -> str:
    body = "\n".join(lines) if lines else "  (none)"
    return f"== {title} ==\n{body}"


def _wind_compass(degrees: int | None) -> str:
    """Convert wind direction in degrees to an 8-point compass label."""
    if degrees is None:
        return ""
    labels = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return " " + labels[round(degrees / 45) % 8]


def _session_block(session: RaceSession, db: Session, user: User) -> list[str]:
    """
    Build a compact AI-readable summary block for one synced session.
    Delegates all DB work to build_session_summary() — no duplicate queries here.
    """
    summary = build_session_summary(session, db, user)
    lines: list[str] = []

    # ── Identity ──────────────────────────────────────────────────────────────
    location_parts = [p for p in [summary.circuit_short_name, summary.country_name] if p]
    location = f" ({', '.join(location_parts)})" if location_parts else ""
    lines.append(f"  Session : {summary.session_name} — {summary.race_name}{location}")
    lines.append(f"  Date    : {_fmt_time(summary.start_time)}")

    # ── Missing-data flags (AI must not guess for any flagged section) ────────
    missing = []
    if not summary.has_lap_data:
        missing.append("no_lap_data")
    if not summary.has_stint_data:
        missing.append("no_stint_data")
    if not summary.has_rc_data:
        missing.append("no_race_control_data")
    if not summary.has_weather_data:
        missing.append("no_weather_data")
    if missing:
        lines.append(f"  Missing : {', '.join(missing)}")

    # ── Lap summary ───────────────────────────────────────────────────────────
    if summary.has_lap_data:
        ls = summary.lap_stats
        lines.append(
            f"  Laps    : {ls.total_rows} rows | "
            f"{ls.driver_count} drivers | max lap {ls.max_lap}"
        )
        # For race/sprint, per-driver data is in finishing_order below.
        # For qualifying/FP, add a compact per-driver max-lap table so the AI
        # can answer "how many laps did driver X complete in qualifying?".
        if summary.session_type not in ("race", "sprint"):
            driver_max: list[tuple[int, int]] = (
                db.query(Lap.driver_number, func.max(Lap.lap_number))
                .filter(Lap.session_id == session.id)
                .group_by(Lap.driver_number)
                .order_by(func.max(Lap.lap_number).desc())
                .all()
            )
            if driver_max:
                shown = driver_max[:_AI_MAX_DRIVER_LAPS]
                extra = len(driver_max) - len(shown)
                suffix = f" ({extra} more not shown)" if extra else ""
                lines.append(f"  Per-driver laps (max lap number recorded){suffix}:")
                for dn, max_lap_n in shown:
                    lines.append(f"    #{dn}: {max_lap_n}")
    else:
        lines.append("  Laps    : GridPulse does not have synced lap data for this session.")

    # ── Finishing order (race / sprint only) ──────────────────────────────────
    if summary.finishing_order:
        lines.append("  Finishing order (derived from lap data — not official results):")
        lines.append("    (max_lap = highest lap number recorded; rows = total lap rows)")
        for e in summary.finishing_order:
            suffix = (
                f"  (+{e.laps_behind} lap{'s' if e.laps_behind != 1 else ''})"
                if e.laps_behind else ""
            )
            lines.append(
                f"    P{e.position}. {e.driver_name} (#{e.driver_number})  "
                f"max_lap={e.max_lap}  rows={e.row_count}{suffix}"
            )

    # ── Tyre strategy ─────────────────────────────────────────────────────────
    if summary.has_stint_data:
        lines.append("  Tyre strategy:")
        if summary.compound_overview:
            total_stints = sum(summary.compound_overview.values())
            overview = ", ".join(
                f"{n}× {c}"
                for c, n in sorted(summary.compound_overview.items(), key=lambda x: -x[1])
            )
            lines.append(
                f"    Overview : {overview}  "
                f"({total_stints} stints, {len(summary.stint_summary)} drivers)"
            )
        for d in summary.stint_summary:
            parts: list[str] = []
            for s in d.stints:
                compound = s.compound or "?"
                if s.lap_start is not None and s.lap_end is not None:
                    lap_range = f"laps {s.lap_start}–{s.lap_end}"
                elif s.lap_start is not None:
                    lap_range = f"from lap {s.lap_start}"
                else:
                    lap_range = "laps ?"
                age = f"{s.tyre_age_at_start} laps old" if s.tyre_age_at_start else "new"
                parts.append(f"S{s.stint_number or '?'} {compound} {lap_range} ({age})")
            lines.append(f"    {d.driver_name} (#{d.driver_number}): {', '.join(parts)}")
    else:
        lines.append("  Tyres   : GridPulse does not have synced stint/tyre data for this session.")

    # ── Weather summary ───────────────────────────────────────────────────────
    if summary.has_weather_data and summary.weather:
        w = summary.weather
        range_parts: list[str] = []
        if w.air_min is not None and w.air_max is not None:
            range_parts.append(f"Air {w.air_min}–{w.air_max} °C")
        if w.track_min is not None and w.track_max is not None:
            range_parts.append(f"Track {w.track_min}–{w.track_max} °C")
        range_parts.append("Rain: yes" if w.had_rain else "Rain: no")
        range_parts.append(f"({w.sample_count} readings)")

        latest_parts: list[str] = []
        if w.latest_sample:
            lw = w.latest_sample
            if lw.air_temperature is not None:
                latest_parts.append(f"Air {lw.air_temperature:.1f} °C")
            if lw.track_temperature is not None:
                latest_parts.append(f"Track {lw.track_temperature:.1f} °C")
            if lw.humidity is not None:
                latest_parts.append(f"Humidity {lw.humidity:.0f}%")
            if lw.wind_speed is not None:
                latest_parts.append(
                    f"Wind {lw.wind_speed:.1f} m/s{_wind_compass(lw.wind_direction)}"
                )
            if lw.rainfall is not None:
                latest_parts.append("raining" if lw.rainfall else "dry")

        weather_line = ", ".join(range_parts)
        if latest_parts:
            weather_line += "; Latest: " + ", ".join(latest_parts)
        lines.append(f"  Weather : {weather_line}")
    else:
        lines.append("  Weather : GridPulse does not have synced weather data for this session.")

    # ── Race control ──────────────────────────────────────────────────────────
    if summary.has_rc_data:
        if summary.key_rc_events:
            lines.append(f"  Key race events ({summary.rc_total} total RC messages):")
            for ev in summary.key_rc_events:
                lap_info = f" (lap {ev.lap_number})" if ev.lap_number is not None else ""
                lines.append(f"    • {ev.label}{lap_info}")

        ai_rc = summary.rc_messages[:_AI_MAX_RC]
        not_shown = summary.rc_total - len(ai_rc)
        note = f" ({not_shown} not shown — blue-flag + routine excluded)" if not_shown else ""

        lines.append(
            f"  Race control — {len(ai_rc)} of "
            f"{summary.rc_total} messages shown{note}:"
        )
        for msg in ai_rc:
            lap_tag = f"[Lap {msg.lap_number}] " if msg.lap_number is not None else ""
            flag_tag = f"[{msg.flag}] " if msg.flag else ""
            lines.append(f"    {lap_tag}{flag_tag}{msg.message}")
    else:
        lines.append(
            "  Race control : GridPulse does not have synced race control data for this session."
        )

    return lines


# ─── Driver reference table ───────────────────────────────────────────────────

def _build_driver_reference(db: Session) -> list[str]:
    """
    Compact mapping of driver numbers to names and teams.
    Lets the AI decode car numbers in race control messages
    (e.g. "CAR 63 (RUS)" → George Russell, Mercedes).
    """
    drivers = (
        db.query(Driver)
        .filter(Driver.driver_number.isnot(None))
        .order_by(Driver.driver_number)
        .all()
    )
    if not drivers:
        return ["  (no driver data)"]

    lines: list[str] = []
    for d in drivers:
        team_name = d.team.name if d.team else "no team"
        abbreviation = f" ({d.code})" if d.code else ""
        lines.append(f"  #{d.driver_number}{abbreviation} {d.full_name} — {team_name}")
    return lines


# ─── Main builder ─────────────────────────────────────────────────────────────

def build_context(user: User, db: Session) -> str:
    """
    Gather relevant GridPulse data for the given user and return it as a
    plain-text context string to be injected into the AI prompt.

    Design principles:
    - Summarise everything — never dump raw rows.
    - Caps and smart selection keep total prompt tokens within model limits.
    - Sensitive fields (password_hash, auth tokens) are never read.
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

    # ── Driver number reference ───────────────────────────────────────────────
    ref_lines = _build_driver_reference(db)
    sections.append(_section("Driver Number Reference (for decoding RC messages)", ref_lines))

    # ── Historical session data ───────────────────────────────────────────────
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
            hist_lines.extend(_session_block(sess, db, user))
            if i < len(synced_sessions) - 1:
                hist_lines.append("")
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
        "  - Official race classifications (finishing positions above are derived",
        "    from lap timing — post-race penalties/DSQs are not reflected)",
        "  - Qualifying results, grid positions, or pole lap times",
        "  - Individual lap times per driver (only aggregate counts are stored)",
        "  - Pit stop durations or exact pit timing",
        "  - Live race timing or telemetry of any kind",
        "  - Car telemetry (speed traces, throttle, brake, GPS position)",
        "  Note: Tyre strategies, weather, and RC messages are stored only for",
        "        sessions synced via the OpenF1 sync script.",
    ]))

    return "\n\n".join(sections)
