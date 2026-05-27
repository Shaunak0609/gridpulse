from pydantic import BaseModel


class AlertTypeResult(BaseModel):
    """
    Counts for one alert type within a single session alert generation run.

    created       — new notification rows written to the database.
    skipped       — alerts that already existed for this (user, type, driver,
                    session) combination; no duplicate was created.
    emails_sent   — emails successfully delivered after the notification was saved.
    emails_failed — email attempts that raised an error; the notification row
                    was still saved, so in-app delivery is never lost.
    """

    created: int
    skipped: int
    emails_sent: int
    emails_failed: int


class SessionAlertGenerationResult(BaseModel):
    """
    Full result returned after running generate_session_alerts() for one session.

    session_id               — the GridPulse sessions.id that was processed.
    session_name             — human-readable name, e.g. "Race" or "Practice 1".
    race_name                — the parent race name, e.g. "Australian Grand Prix".
    is_synced                — False when the session has no OpenF1 session key;
                               in that case no alerts are generated and message
                               explains why.
    favorite_drivers_checked — number of favourite drivers that had at least one
                               lap, stint, or race control row in this session.
                               Drivers with no data at all are not counted.
    alerts                   — per-alert-type breakdown keyed by notification type
                               string (e.g. "favorite_driver_fastest_lap").
    total_created            — sum of created across all alert types.
    total_skipped            — sum of skipped across all alert types.
    emails_sent              — sum of emails_sent across all alert types.
    emails_failed            — sum of emails_failed across all alert types.
    message                  — set when is_synced is False to explain why no
                               alerts were generated.
    """

    session_id: int
    session_name: str | None = None
    race_name: str | None = None
    is_synced: bool
    favorite_drivers_checked: int = 0
    alerts: dict[str, AlertTypeResult] = {}
    total_created: int = 0
    total_skipped: int = 0
    emails_sent: int = 0
    emails_failed: int = 0
    message: str | None = None
