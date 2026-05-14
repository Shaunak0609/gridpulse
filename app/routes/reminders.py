from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.models.notification import Notification
from app.models.reminder import Reminder
from app.models.session import Session as RaceSession
from app.models.user import User
from app.schemas.reminder import ReminderCreate, ReminderResponse

router = APIRouter(prefix="/reminders", tags=["reminders"])


@router.post("", response_model=ReminderResponse, status_code=status.HTTP_201_CREATED)
def create_reminder(
    body: ReminderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # --- Resolve session_id and auto-populate race_id from session ---
    resolved_race_id = body.race_id
    if body.session_id is not None:
        session = db.query(RaceSession).filter(RaceSession.id == body.session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session with id {body.session_id} not found.",
            )
        resolved_race_id = session.race_id

    # --- Duplicate check ---
    if body.session_id is not None:
        existing = db.query(Reminder).filter(
            Reminder.user_id == current_user.id,
            Reminder.session_id == body.session_id,
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have a reminder for this session.",
            )
    elif resolved_race_id is not None:
        existing = db.query(Reminder).filter(
            Reminder.user_id == current_user.id,
            Reminder.race_id == resolved_race_id,
            Reminder.session_id == None,    # noqa: E711
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="You already have a reminder for this race.",
            )

    reminder = Reminder(
        user_id=current_user.id,
        race_id=resolved_race_id,
        session_id=body.session_id,
        title=body.title,
        reminder_time=body.reminder_time,
    )
    db.add(reminder)

    notification = Notification(
        user_id=current_user.id,
        type="reminder_created",
        title="Reminder created",
        message=f'Your reminder "{body.title}" has been set.',
        related_race_id=resolved_race_id,
    )
    db.add(notification)

    db.commit()
    db.refresh(reminder)
    return reminder


@router.get("", response_model=list[ReminderResponse])
def get_reminders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return (
        db.query(Reminder)
        .filter(Reminder.user_id == current_user.id)
        .order_by(Reminder.reminder_time)
        .all()
    )


@router.delete("/{reminder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_reminder(
    reminder_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    reminder = db.query(Reminder).filter(Reminder.id == reminder_id).first()

    if not reminder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Reminder with id {reminder_id} not found.",
        )

    if reminder.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this reminder.",
        )

    db.delete(reminder)
    db.commit()
