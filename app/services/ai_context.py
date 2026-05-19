import os
from collections import Counter, defaultdict
from datetime import datetime, timezone

from sqlalchemy import distinct, func
from sqlalchemy.orm import Session

from app.models.driver import Driver
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

# Context budget caps — keep total prompt tokens well under the Groq free-tier
# TPM limit for llama-3.1-8b-instant (6 000 TPM).
_MAX_STANDINGS = 10
_MAX_SESSIONS = 5
_MAX_REMINDERS = 3
_MAX_NOTIFICATIONS = 3
_MAX_SYNCED_SESSIONS = 3    # most-recent synced sessions to describe

# Race control: key-events summary is always included in full.
# The curated message list is capped at _MAX_RC_MESSAGES (blue-flag lapping
# messages excluded; other routine ones trimmed last).
_MAX_RC_MESSAGES = 40


def _fmt_time(dt: datetime | None) -> str:
    if not dt:
        return "TBC"
    utc = dt.astimezone(timezone.utc)
    return utc.strftime("%a %d %b %Y, %H:%M UTC")


def _section(title: str, lines: list[str]) -> str:
    body = "\n".join(lines) if lines else "  (none)"
    return f"== {title} ==\n{body}"


# ─── Historical session helpers ───────────────────────────────────────────────

def _build_driver_name_map(db: Session) -> dict[int, str]:
    return {
        d.driver_number: d.full_name
        for d in db.query(Driver).all()
        if d.driver_number is not None
    }


def _weather_summary(session_id: int, db: Session) -> str | None:
    """One-line weather summary (min/max air + track temp, rainfall)."""
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


def _per_driver_stints(
    session_id: int,
    db: Session,
    driver_name_map: dict[int, str],
) -> list[str] | None:
    """
    Per-driver tyre strategy — one compact line per driver.
    Also prepends a compound-usage overview line.

    Example:
      Overview : 3× HARD, 2× MEDIUM, 1× SOFT  (across 6 stints, 3 drivers)
      George Russell (#63): S1 MEDIUM laps 1–18 (new), S2 HARD laps 19–58 (new)
    """
    stints = (
        db.query(Stint)
        .filter(Stint.session_id == session_id)
        .order_by(Stint.driver_number, Stint.stint_number)
        .all()
    )
    if not stints:
        return None

    # Compound overview
    compound_counts = Counter(s.compound for s in stints if s.compound)
    if compound_counts:
        overview = ", ".join(
            f"{n}× {c}" for c, n in compound_counts.most_common()
        )
        overview_line = f"  Overview : {overview}  ({len(stints)} stints, {len(set(s.driver_number for s in stints))} drivers)"
    else:
        overview_line = f"  Overview : {len(stints)} stints (compound data unavailable)"

    # Per-driver breakdown
    driver_stints: dict[int, list[Stint]] = defaultdict(list)
    for s in stints:
        driver_stints[s.driver_number].append(s)

    lines: list[str] = [overview_line]
    for dn in sorted(driver_stints):
        name = driver_name_map.get(dn, f"Driver #{dn}")
        parts: list[str] = []
        for s in driver_stints[dn]:
            compound = s.compound or "?"
            if s.lap_start is not None and s.lap_end is not None:
                lap_range = f"laps {s.lap_start}–{s.lap_end}"
            elif s.lap_start is not None:
                lap_range = f"from lap {s.lap_start}"
            else:
                lap_range = "laps ?"
            age = (
                f"{s.tyre_age_at_start} laps old"
                if s.tyre_age_at_start
                else "new"
            )
            parts.append(f"S{s.stint_number or '?'} {compound} {lap_range} ({age})")
        lines.append(f"    {name} (#{dn}): {', '.join(parts)}")

    return lines


def _key_rc_events(rc_messages: list) -> list[str]:
    """
    Scan all race control messages and return a short bullet list of the most
    significant event types with the lap number of their first occurrence.
    Used as a high-priority summary before the curated message list.
    """
    keywords = [
        ("SAFETY CAR DEPLOYED",   "Safety car deployed"),
        ("SAFETY CAR IN",         "Safety car recalled"),
        ("VIRTUAL SAFETY CAR",    "Virtual safety car (VSC)"),
        # OpenF1 encodes VSC as "VSC DEPLOYED" / "VSC ENDING"
        ("VSC DEPLOYED",          "Virtual safety car (VSC)"),
        ("RED FLAG",              "Red flag"),
        # OpenF1 encodes DRS as "OVERTAKE ENABLED/DISABLED"
        ("DRS ENABLED",           "DRS enabled"),
        ("DRS DISABLED",          "DRS disabled"),
        ("OVERTAKE ENABLED",      "DRS enabled (overtake)"),
        ("OVERTAKE DISABLED",     "DRS disabled (overtake)"),
        ("PIT LANE OPEN",         "Pit lane open"),
        ("PIT LANE CLOSED",       "Pit lane closed"),
        ("INVESTIGATE",           "Investigation/penalty"),
        ("PENALTY",               "Penalty"),
        ("DRIVE THROUGH",         "Drive-through penalty"),
        ("STOP AND GO",           "Stop-and-go penalty"),
        ("STOP-AND-GO",           "Stop-and-go penalty"),
        ("RETIRED",               "Retirement"),
        ("MEDICAL CAR",           "Medical car deployed"),
    ]

    seen_labels: set[str] = set()
    events: list[str] = []

    for msg in rc_messages:
        text = (msg.message or "").upper()
        flag = (msg.flag or "").upper()
        combined = text + " " + flag

        for keyword, label in keywords:
            if keyword in combined and label not in seen_labels:
                lap_info = f" (lap {msg.lap_number})" if msg.lap_number is not None else ""
                events.append(f"    • {label}{lap_info}")
                seen_labels.add(label)

    return events


def _select_rc_messages(
    rc_messages: list,
    max_count: int,
) -> tuple[list, int, int]:
    """
    Smart-select up to max_count RC messages for the context, prioritising
    the most informative ones.

    Priority (highest first):
      1. Non-CLEAR, non-BLUE flagged messages (YELLOW, RED, GREEN, CHEQUERED…)
      2. Messages matching incident/event keywords (VSC, investigation, penalty,
         pit lane, session boundaries, weather, track limits, marshals)
      3. CLEAR messages and other routine ones (fill remaining slots)

    BLUE flag messages (lapping notifications) are always excluded — they are
    repetitive and low-information; the key-events summary covers what matters.

    Returns (selected_sorted_by_date, omitted_count, blue_flag_count).
    """
    BLUE_FLAGS = {"BLUE"}
    PRIORITY_FLAGS = {"GREEN", "YELLOW", "DOUBLE YELLOW", "RED", "CHEQUERED", "SAFETY CAR"}
    IMPORTANT_KEYWORDS = [
        "VSC", "VIRTUAL SAFETY CAR", "SAFETY CAR", "MEDICAL CAR",
        "INVESTIGATE", "PENALTY", "DRIVE THROUGH", "STOP AND GO", "STOP-AND-GO",
        "RETIRED", "INCIDENT", "SESSION STARTED", "SESSION FINISHED",
        "PIT EXIT", "PIT LANE", "MARSHALS", "RISK OF RAIN",
        "CHEQUERED FLAG", "OVERTAKE ENABLED", "OVERTAKE DISABLED",
        "TIME DELETED", "TRACK LIMITS",
    ]

    blue_count = 0
    high_priority: list = []
    low_priority: list = []

    for msg in rc_messages:
        flag = (msg.flag or "").upper()
        text = (msg.message or "").upper()

        if flag in BLUE_FLAGS:
            blue_count += 1
            continue

        if flag in PRIORITY_FLAGS or any(kw in text for kw in IMPORTANT_KEYWORDS):
            high_priority.append(msg)
        else:
            low_priority.append(msg)

    # Fill slots: high-priority first, then low-priority
    selected = high_priority[:max_count]
    remaining = max_count - len(selected)
    if remaining > 0:
        selected += low_priority[:remaining]

    # Restore chronological order
    _epoch = datetime(1970, 1, 1, tzinfo=timezone.utc)
    selected.sort(key=lambda m: m.date or _epoch)

    omitted = len(high_priority) - len([m for m in selected if m in set(high_priority)])
    omitted += max(0, len(low_priority) - remaining)
    return selected, omitted, blue_count


def _finishing_order(
    session_id: int,
    session_type: str,
    db: Session,
    driver_name_map: dict[int, str],
) -> list[str] | None:
    """
    Derive approximate finishing order from lap data for race and sprint sessions.

    Sorted by max lap_number DESC (not row count — OpenF1 has gaps), then by
    the date_start of the final recorded lap ASC as a tiebreaker.

    Each line includes max_lap (highest lap number seen) and rows (total lap
    row count) so the AI can infer lapped drivers and retirements.

    Returns None for non-race sessions or when no lap data is stored.
    """
    if session_type not in ("race", "sprint"):
        return None

    laps = db.query(Lap).filter(Lap.session_id == session_id).all()
    if not laps:
        return None

    # Track (max_lap_number, date_start_of_that_lap, row_count) per driver
    driver_last: dict[int, tuple[int, datetime | None, int]] = {}
    for lap in laps:
        dn = lap.driver_number
        if dn not in driver_last:
            driver_last[dn] = (lap.lap_number, lap.date_start, 1)
        elif lap.lap_number > driver_last[dn][0]:
            driver_last[dn] = (lap.lap_number, lap.date_start, driver_last[dn][2] + 1)
        else:
            driver_last[dn] = (driver_last[dn][0], driver_last[dn][1], driver_last[dn][2] + 1)

    _far_future = datetime(9999, 1, 1, tzinfo=timezone.utc)

    ordered = sorted(
        driver_last.keys(),
        key=lambda dn: (
            -driver_last[dn][0],               # higher max lap = ahead
            driver_last[dn][1] or _far_future,  # earlier final-lap start = ahead
        ),
    )

    max_lap_number = max(v[0] for v in driver_last.values())
    lines: list[str] = []
    for pos, dn in enumerate(ordered, 1):
        name = driver_name_map.get(dn, f"Driver #{dn}")
        max_lap, _, row_count = driver_last[dn]
        laps_behind = max_lap_number - max_lap
        suffix = f"  (+{laps_behind} lap{'s' if laps_behind != 1 else ''})" if laps_behind else ""
        lines.append(
            f"    P{pos}. {name} (#{dn})  "
            f"max_lap={max_lap}  rows={row_count}{suffix}"
        )

    return lines


def _session_block(session: RaceSession, db: Session) -> list[str]:
    """
    Build a compact summary block for one synced session.

    Design principle: summarise everything — never dump raw rows.
    - Laps: aggregate counts + derived finishing order only.
    - Stints: compound overview + one line per driver.
    - Weather: single summary line.
    - RC messages: key-events bullet list (always) + curated chronological
      list capped at _MAX_RC_MESSAGES (blue-flag messages excluded).
    """
    lines: list[str] = []
    driver_name_map = _build_driver_name_map(db)

    race_name = session.race.name if session.race else f"Race {session.race_id}"
    location_parts = [
        p for p in [session.circuit_short_name, session.country_name] if p
    ]
    location = f" ({', '.join(location_parts)})" if location_parts else ""
    lines.append(f"  Session : {session.session_name} — {race_name}{location}")
    lines.append(f"  Date    : {_fmt_time(session.start_time)}")

    # ── Lap summary (aggregate only) ──────────────────────────────────────────
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
        lines.append(f"  Laps    : {lap_count} rows stored across {driver_count} drivers")
    else:
        lines.append("  Laps    : none stored (run sync script to ingest)")

    # ── Finishing order (race / sprint only) ──────────────────────────────────
    finishing = _finishing_order(session.id, session.session_type, db, driver_name_map)
    if finishing:
        lines.append("  Finishing order (derived from lap data — not official results):")
        lines.append("    (max_lap = highest lap number recorded; rows = lap row count)")
        lines.extend(finishing)

    # ── Tyre strategy ─────────────────────────────────────────────────────────
    stint_lines = _per_driver_stints(session.id, db, driver_name_map)
    if stint_lines:
        lines.append("  Tyre strategy:")
        lines.extend(stint_lines)
    else:
        lines.append("  Tyres   : no stint data stored")

    # ── Weather summary ───────────────────────────────────────────────────────
    weather_line = _weather_summary(session.id, db)
    if weather_line:
        lines.append(f"  Weather : {weather_line}")
    else:
        lines.append("  Weather : no weather data stored")

    # ── Race control messages ─────────────────────────────────────────────────
    rc_all = (
        db.query(RaceControlMessage)
        .filter(RaceControlMessage.session_id == session.id)
        .order_by(RaceControlMessage.date)
        .all()
    )
    if rc_all:
        # Key-events summary (no cap — always fully included)
        key_events = _key_rc_events(rc_all)
        if key_events:
            lines.append(f"  Key race events ({len(rc_all)} total RC messages):")
            lines.extend(key_events)

        # Curated chronological list (capped, blue-flag messages excluded)
        selected, omitted, blue_count = _select_rc_messages(rc_all, _MAX_RC_MESSAGES)

        note_parts: list[str] = []
        if blue_count:
            note_parts.append(f"{blue_count} blue-flag lapping messages excluded")
        if omitted > 0:
            note_parts.append(f"{omitted} other routine messages omitted")
        note = f" ({'; '.join(note_parts)}; full log in session detail page)" if note_parts else ""

        lines.append(f"  Race control — {len(selected)} of {len(rc_all)} messages shown{note}:")
        for msg in selected:
            lap_tag = f"[Lap {msg.lap_number}] " if msg.lap_number is not None else ""
            flag_tag = f"[{msg.flag}] " if msg.flag else ""
            lines.append(f"    {lap_tag}{flag_tag}{msg.message}")
    else:
        lines.append("  Race control : no messages stored")

    return lines


# ─── Driver reference table ───────────────────────────────────────────────────

def _build_driver_reference(db: Session) -> list[str]:
    """
    Compact reference mapping driver numbers to names and teams.
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
    - Caps and smart selection keep the total prompt tokens within model limits.
    - Sensitive fields (password_hash, google_sub, auth tokens) are never read.
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
            hist_lines.extend(_session_block(sess, db))
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
