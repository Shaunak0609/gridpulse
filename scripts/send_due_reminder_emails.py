import sys
import os
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# app.database.database calls load_dotenv(), so .env is loaded before anything
# else in this script reads environment variables.
from app.database.database import SessionLocal
from app.models.reminder import Reminder
from app.models.user import User
from app.services.email_service import send_email


def build_email_body(reminder: Reminder) -> str:
    race_name = reminder.race.name if reminder.race else reminder.title
    username = reminder.user.username or reminder.user.email

    when = (
        reminder.reminder_time.strftime("%-d %B %Y at %H:%M UTC")
        if reminder.reminder_time
        else "soon"
    )

    return (
        f"Hi {username},\n\n"
        f"This is your GridPulse reminder for the {race_name}.\n\n"
        f"You set this reminder for: {when}\n\n"
        f"Head to GridPulse to check the latest standings and calendar.\n\n"
        f"— The GridPulse team\n\n"
        f"To stop receiving these emails, turn off race reminders in your GridPulse settings."
    )


def send_due_reminder_emails() -> None:
    now = datetime.now(timezone.utc)

    db = SessionLocal()
    try:
        due_reminders = (
            db.query(Reminder)
            .join(User)
            .filter(
                Reminder.reminder_time <= now,
                Reminder.email_sent == False,          # noqa: E712
                User.email_notifications_enabled == True,   # noqa: E712
                User.calendar_email_reminders_enabled == True,  # noqa: E712
            )
            .all()
        )

        total = len(due_reminders)
        print(f"Found {total} due reminder(s) to send.\n")

        if total == 0:
            return

        sent = 0
        failed = 0

        for reminder in due_reminders:
            race_label = reminder.race.name if reminder.race else reminder.title
            print(f"  Sending: reminder #{reminder.id} — {race_label} → {reminder.user.email}")

            try:
                send_email(
                    to=reminder.user.email,
                    subject=f"GridPulse Reminder: {race_label}",
                    body=build_email_body(reminder),
                )

                reminder.email_sent = True
                reminder.email_sent_at = datetime.now(timezone.utc)
                reminder.sent = True
                db.commit()

                print(f"    OK — email sent, reminder marked as sent.")
                sent += 1

            except RuntimeError as e:
                print(f"    FAILED — {e}")
                db.rollback()
                failed += 1

        print(f"\nDone. {sent} sent, {failed} failed.")

    finally:
        db.close()


if __name__ == "__main__":
    send_due_reminder_emails()
