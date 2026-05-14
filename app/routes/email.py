from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database.database import get_db
from app.models.user import User
from app.services.email_service import send_email
from app.services.reminder_email_service import process_due_reminders

router = APIRouter(prefix="/email", tags=["email"])


@router.post("/test", status_code=status.HTTP_200_OK)
def send_test_email(current_user: User = Depends(get_current_user)):
    if not current_user.email_notifications_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Email notifications are disabled. Enable them via PUT /users/me/email-preferences first.",
        )

    try:
        send_email(
            to=current_user.email,
            subject="GridPulse test email",
            body=(
                f"Hi{' ' + current_user.username if current_user.username else ''},\n\n"
                "Your GridPulse email notifications are working.\n\n"
                "You will receive reminder emails for races you have set reminders for.\n\n"
                "— The GridPulse team"
            ),
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    return {"message": f"Test email sent to {current_user.email}."}


# Development / manual trigger — no background scheduler yet.
# In production this logic will be called by a scheduled job, not an endpoint.
@router.post("/send-due-reminders", status_code=status.HTTP_200_OK)
def trigger_due_reminder_emails(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        result = process_due_reminders(db)
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )

    return {
        "note": "Manual trigger — will be replaced by a scheduler in production.",
        "total_due": result["total"],
        "sent": result["sent"],
        "failed": result["failed"],
    }
