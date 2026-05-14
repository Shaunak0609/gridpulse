from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.reminder import Reminder
from app.models.user import User
from app.services.email_service import send_email


def _build_body(reminder: Reminder) -> str:
    username = reminder.user.username or reminder.user.email
    when = (
        reminder.reminder_time.strftime("%-d %B %Y at %H:%M UTC")
        if reminder.reminder_time
        else "soon"
    )

    if reminder.session_id and reminder.session:
        session_name = reminder.session.session_name
        race_name = reminder.race.name if reminder.race else "the race weekend"
        event_line = f"This is your GridPulse reminder for {session_name} at the {race_name}."
    else:
        race_name = reminder.race.name if reminder.race else reminder.title
        event_line = f"This is your GridPulse reminder for the {race_name}."

    return (
        f"Hi {username},\n\n"
        f"{event_line}\n\n"
        f"You set this reminder for: {when}\n\n"
        f"Head to GridPulse to check the latest standings and calendar.\n\n"
        f"— The GridPulse team\n\n"
        f"To stop receiving these emails, turn off race reminders in your GridPulse settings."
    )


def process_due_reminders(db: Session) -> dict:
    """
    Find all due, unsent reminders for users who have opted into email
    notifications, send each one, and mark it as sent.

    Returns a summary dict: {"total": int, "sent": int, "failed": int}
    """
    now = datetime.now(timezone.utc)

    due = (
        db.query(Reminder)
        .join(User)
        .filter(
            Reminder.reminder_time <= now,
            Reminder.email_sent == False,            # noqa: E712
            User.email_notifications_enabled == True,     # noqa: E712
            User.calendar_email_reminders_enabled == True,  # noqa: E712
        )
        .all()
    )

    sent = 0
    failed = 0

    for reminder in due:
        if reminder.session_id and reminder.session:
            race_label = reminder.race.name if reminder.race else "Race Weekend"
            subject = f"GridPulse Reminder: {reminder.session.session_name} – {race_label}"
        else:
            race_label = reminder.race.name if reminder.race else reminder.title
            subject = f"GridPulse Reminder: {race_label}"
        try:
            send_email(
                to=reminder.user.email,
                subject=subject,
                body=_build_body(reminder),
            )
            reminder.email_sent = True
            reminder.email_sent_at = datetime.now(timezone.utc)
            reminder.sent = True
            db.commit()
            sent += 1
        except RuntimeError:
            db.rollback()
            failed += 1

    return {"total": len(due), "sent": sent, "failed": failed}
