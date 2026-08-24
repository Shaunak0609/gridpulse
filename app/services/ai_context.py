import os
from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.driver import Driver
from app.models.favorite_driver import FavoriteDriver
from app.models.favorite_team import FavoriteTeam
from app.models.lap import Lap
from app.models.notification import Notification
from app.models.race_result import RaceResult
from app.models.reminder import Reminder
from app.models.session import Session as RaceSession
from app.models.standing import DriverStanding
from app.models.user import User
from app.services.analytics_service import build_session_analytics
from app.services.session_dashboard import build_session_summary
from app.services.strategy_dashboard import build_strategy_summary

SEASON = int(os.getenv("F1_SEASON", "2026"))

# Context caps. These used to be tight enough to fit Groq's free-tier 6 000 TPM
# limit (llama-3.1-8b-instant); now that generation runs on OpenAI (much larger
# context window, low per-token cost), historical session coverage is
# unbounded — every synced session is included, not just the last few — and
# the remaining per-section caps below just match the service-level caps used
# by the dashboard endpoints (a full F1 grid is 20-22 drivers).
_MAX_STANDINGS = 10
_MAX_SESSIONS = 5
_MAX_REMINDERS = 3
_MAX_NOTIFICATIONS = 3
_MAX_DRIVER_ALERTS = 5      # favourite-driver alert entries to include

_AI_MAX_RC = 40             # RC messages per session (matches service cap)
_AI_MAX_DRIVER_LAPS = 22    # per-driver lap rows for qualifying/FP sessions
_AI_MAX_STRATEGY_DRIVERS = 22  # per-driver strategy rows in AI context
_AI_MAX_INSIGHTS = 4            # rule-based insight sentences to include
_AI_MAX_ANALYTICS_DRIVERS = 22 # per-driver pace rows in analytics context

# Human-readable label and data source for each favourite-driver alert type.
_ALERT_TYPE_META: dict[str, tuple[str, str]] = {
    "favorite_driver_fastest_lap":    ("Fastest lap in session",        "lap data"),
    "favorite_driver_strategy":       ("Tyre strategy summary",         "stint data"),
    "favorite_driver_rc_mention":     ("Race control mention",          "race control data"),
    "favorite_driver_lap_comparison": ("Lap comparison note",           "lap data"),
    "favorite_driver_standing":       ("Championship standings update", "standings data"),
    "favorite_driver_wins":           ("Race wins update",              "standings data"),
}


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


def _ai_strategy_lines(session: RaceSession, db: Session, user: User) -> list[str]:
    """
    Compact strategy context for one synced session.
    Covers compound usage, stop counts, pit windows, per-driver sequences,
    and top insights. RC events and weather are emitted separately in
    _session_block() to avoid doubling the token budget.
    """
    summary = build_strategy_summary(session, db, user)

    if not summary.has_stint_data:
        return ["  Tyres   : GridPulse does not have synced stint/tyre data for this session."]

    lines: list[str] = ["  Strategy:"]

    # Compound usage overview
    if summary.compound_usage:
        parts: list[str] = []
        for cu in summary.compound_usage:
            part = f"{cu.compound}×{cu.stint_count}"
            if cu.avg_stint_laps is not None:
                part += f" avg {cu.avg_stint_laps}L"
            parts.append(part)
        lines.append("    Compounds  : " + ", ".join(parts))

    # Stop-count summary (counts only — driver-level detail is in per-driver sequences)
    if summary.stop_count_groups:
        stop_parts: list[str] = []
        for stops in sorted(summary.stop_count_groups):
            n = len(summary.stop_count_groups[stops])
            label = "stop" if stops == 1 else "stops"
            stop_parts.append(f"{stops} {label}: {n} driver{'s' if n != 1 else ''}")
        lines.append("    Pit stops  : " + "; ".join(stop_parts))

    # Pit windows
    if summary.pit_windows:
        pw_parts: list[str] = []
        for pw in summary.pit_windows:
            if pw.lap_min == pw.lap_max:
                pw_parts.append(f"Lap {pw.lap_min} ({pw.driver_count} drivers)")
            else:
                pw_parts.append(f"Laps {pw.lap_min}–{pw.lap_max} ({pw.driver_count} drivers)")
        lines.append("    Pit windows: " + "; ".join(pw_parts))

    # Per-driver compound sequences (compact, capped)
    shown = summary.driver_strategies[:_AI_MAX_STRATEGY_DRIVERS]
    extra = len(summary.driver_strategies) - len(shown)
    suffix = f" ({extra} more not shown)" if extra else ""
    if shown:
        lines.append(f"    Per-driver sequences{suffix}:")
        for ds in shown:
            seq = " → ".join(ds.compound_sequence) if ds.compound_sequence else "unknown"
            stop_str = f"{ds.stop_count} stop{'s' if ds.stop_count != 1 else ''}"
            long_str = f", longest {ds.longest_stint_laps}L" if ds.longest_stint_laps else ""
            lines.append(
                f"      {ds.driver_name} (#{ds.driver_number}): {seq} [{stop_str}{long_str}]"
            )

    # Top rule-based insights
    for insight in summary.insights[:_AI_MAX_INSIGHTS]:
        lines.append(f"    • {insight}")

    return lines


def _ai_analytics_lines(session: RaceSession, db: Session, user: User) -> list[str]:
    """
    Compact pace analytics for one synced session.

    Adds per-driver fastest and average lap times, compound pace averages,
    and safety-car / red-flag lap numbers (which explain anomalous slow laps).
    RC and weather are emitted separately in _session_block — no duplication.

    Skipped entirely when has_lap_data is False — _session_block already emits
    the 'Missing: no_lap_data' flag, so we avoid a redundant line.
    """
    try:
        summary = build_session_analytics(session, db, user)
    except Exception:
        return []

    if not summary.has_lap_data:
        return []

    lines: list[str] = ["  Analytics:"]

    # Session-level pace stats
    if summary.session_fastest_lap is not None:
        lines.append(
            f"    Session fastest: {summary.session_fastest_lap:.3f}s "
            f"({summary.session_fastest_driver})"
        )
    if summary.session_avg_lap is not None:
        lines.append(f"    Session avg    : {summary.session_avg_lap:.3f}s (all timed laps)")

    # Per-driver pace — all drivers with at least one timed lap, capped
    drivers_with_data = [dp for dp in summary.driver_pace if dp.fastest_lap is not None]
    shown = drivers_with_data[:_AI_MAX_ANALYTICS_DRIVERS]
    extra = len(drivers_with_data) - len(shown)
    if shown:
        suffix = f" ({extra} more not shown)" if extra else ""
        lines.append(f"    Per-driver pace{suffix}:")
        for dp in shown:
            avg_str = (
                f", avg {dp.average_lap:.3f}s"
                if dp.average_lap is not None
                else ""
            )
            lines.append(
                f"      {dp.driver_name} (#{dp.driver_number}): "
                f"fastest {dp.fastest_lap:.3f}s{avg_str}"
            )

    # Compound pace averages
    if summary.has_compound_pace and summary.compound_pace:
        parts: list[str] = []
        for cp in summary.compound_pace:
            if cp.avg_lap_time is not None:
                parts.append(
                    f"{cp.compound} avg {cp.avg_lap_time:.3f}s ({cp.sample_lap_count} laps)"
                )
        if parts:
            lines.append("    Compound pace  : " + "; ".join(parts))
    elif not summary.has_compound_pace:
        lines.append("    Compound pace  : unavailable (stints lack lap_start/lap_end ranges)")

    # Safety car and red flag laps — important for pace interpretation
    if summary.safety_car_laps:
        laps_str = ", ".join(str(l) for l in summary.safety_car_laps[:8])
        lines.append(
            f"    Safety car laps: {laps_str} — lap times on these laps are not race pace"
        )
    if summary.red_flag_laps:
        laps_str = ", ".join(str(l) for l in summary.red_flag_laps[:5])
        lines.append(f"    Red flag laps  : {laps_str}")

    if summary.data_note:
        lines.append(f"    Note: {summary.data_note}")

    return lines


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

    # ── Official race result (race sessions only, when synced) ────────────────
    # Authoritative — sourced from Jolpica's official classification, so it
    # reflects penalties/DSQs that the lap-derived finishing order below
    # cannot. When present, this replaces the derived block entirely to avoid
    # showing two possibly-conflicting finishing orders for the same session.
    official_results = []
    if summary.session_type == "race":
        official_results = (
            db.query(RaceResult)
            .filter(RaceResult.session_id == session.id)
            .order_by(RaceResult.position.is_(None), RaceResult.position)
            .all()
        )

    if official_results:
        lines.append("  Official Race Result (authoritative — reflects penalties/DSQs):")
        for rr in official_results:
            driver_name = rr.driver.full_name if rr.driver else "Unknown driver"
            team_name = f", {rr.team.name}" if rr.team else ""
            pos = f"P{rr.position}" if rr.position is not None else rr.position_text or "?"
            status_flag = f"  [{rr.status}]" if rr.status and rr.status != "Finished" else ""
            points_str = f", {rr.points:g} pts" if rr.points is not None else ""
            lines.append(
                f"    {pos}. {driver_name} (#{rr.driver.driver_number if rr.driver else '?'}"
                f"{team_name}){status_flag}{points_str}"
            )
    # ── Finishing order (race / sprint only) — fallback when no official result ──
    elif summary.finishing_order:
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

    # ── Pace analytics ───────────────────────────────────────────────────────
    lines.extend(_ai_analytics_lines(session, db, user))

    # ── Tyre / strategy ───────────────────────────────────────────────────────
    lines.extend(_ai_strategy_lines(session, db, user))

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


# ─── Favourite-driver alert section ──────────────────────────────────────────

def _build_driver_alerts_section(user: User, db: Session) -> list[str]:
    """
    Return compact lines for the user's most recent favourite-driver alerts.

    Each entry includes the alert type label, driver name, session label, and
    the data source that triggered it. The pre-computed message is included so
    the AI can answer questions about detected events without re-querying the DB.

    Capped at _MAX_DRIVER_ALERTS entries to stay within token limits.
    """
    alerts = (
        db.query(Notification)
        .filter(
            Notification.user_id == user.id,
            Notification.type.like("favorite_driver_%"),
        )
        .order_by(Notification.created_at.desc())
        .limit(_MAX_DRIVER_ALERTS)
        .all()
    )
    if not alerts:
        return ["  (no favourite-driver alerts generated yet)"]

    lines: list[str] = []
    for n in alerts:
        label, source = _ALERT_TYPE_META.get(n.type, (n.type, "unknown"))

        driver_name = (
            n.related_driver.full_name if n.related_driver else "unknown driver"
        )
        session_label = "not linked to a specific session"
        if n.related_session:
            race_name = (
                n.related_session.race.name
                if n.related_session.race
                else "Unknown Race"
            )
            session_label = f"{race_name} {n.related_session.session_name}"

        status = "unread" if not n.read else "read"
        lines.append(
            f"  [{label}] {driver_name} | {session_label} | source: {source} | {status}"
        )
        if n.message:
            lines.append(f"    {n.message}")

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

    # ── Recent notifications (non-driver alerts only) ─────────────────────────
    # Favourite-driver alerts have their own dedicated section below — this
    # section covers other notification types such as reminder_created.
    recent_notifications = (
        db.query(Notification)
        .filter(
            Notification.user_id == user.id,
            ~Notification.type.like("favorite_driver_%"),
        )
        .order_by(Notification.created_at.desc())
        .limit(_MAX_NOTIFICATIONS)
        .all()
    )
    notif_lines = [
        f"  - {n.title}" + (f": {n.message}" if n.message else "")
        for n in recent_notifications
    ]
    sections.append(_section("Recent Notifications", notif_lines))

    # ── Favourite-driver alerts ───────────────────────────────────────────────
    alert_lines = _build_driver_alerts_section(user, db)
    sections.append(_section(
        f"Favourite-Driver Alerts (last {_MAX_DRIVER_ALERTS}, most recent first)",
        alert_lines,
    ))

    # ── Driver number reference ───────────────────────────────────────────────
    ref_lines = _build_driver_reference(db)
    sections.append(_section("Driver Number Reference (for decoding RC messages)", ref_lines))

    # ── Historical session data ───────────────────────────────────────────────
    # Every synced session is included — no recency cap. OpenAI's larger
    # context window and low per-token cost make the old "last 2 sessions"
    # limit unnecessary, and it was the main reason the assistant couldn't
    # answer questions about anything but the most recent race weekend.
    synced_sessions = (
        db.query(RaceSession)
        .filter(RaceSession.openf1_session_key.isnot(None))
        .order_by(RaceSession.start_time.desc())
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
            f"(all {len(synced_sessions)} synced, most recent first)"
        )
        sections.append(_section(title, hist_lines))
    else:
        sections.append(_section("Historical Session Data", [
            "  No sessions have been synced from OpenF1 yet.",
            "  Run: python scripts/sync_openf1_session.py --session-key <key>",
        ]))

    # ── Explicit data limitations ─────────────────────────────────────────────
    sections.append(_section("Data NOT Available in GridPulse", [
        "  - Qualifying results, grid positions for quali/practice, or pole lap times",
        "  - Full per-lap time sequences (only fastest, average, and sector best",
        "    times are available per driver via the Analytics section above)",
        "  - Pit stop durations or exact pit timing",
        "  - Live race timing or telemetry of any kind",
        "  - Car telemetry (speed traces, throttle, brake, GPS position)",
        "  Note: Official race classifications (with penalties/DSQs reflected) ARE",
        "        available for race sessions where an 'Official Race Result' block",
        "        appears above — sourced from Jolpica. If that block is absent for a",
        "        given race session, only the lap-derived finishing order exists,",
        "        which does NOT reflect post-race penalties or DSQs.",
        "  Note: Lap times, tyre strategies, weather, and RC messages are stored",
        "        only for sessions synced via the OpenF1 sync script.",
    ]))

    return "\n\n".join(sections)
