from sqlalchemy import Boolean, Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    # nullable so Google users (who have no password) are valid rows
    password_hash = Column(String, nullable=True)
    timezone = Column(String, nullable=True, default="UTC")
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # "local" for email/password accounts, "google" for Google sign-in
    auth_provider = Column(String, nullable=False, default="local")
    # Google's unique, permanent identifier for a user (the "sub" field in the ID token)
    google_sub = Column(String, unique=True, nullable=True, index=True)
    profile_picture_url = Column(String, nullable=True)

    # Email notification preferences — all default to False (opt-in)
    email_notifications_enabled = Column(Boolean, nullable=False, server_default="false")
    calendar_email_reminders_enabled = Column(Boolean, nullable=False, server_default="false")
    favorite_driver_email_alerts_enabled = Column(Boolean, nullable=False, server_default="false")

    # In-app notification preferences — defaults to True (opt-out)
    # Users who favourite a driver expect to see updates; they can turn this off if not wanted.
    favorite_driver_notifications_enabled = Column(Boolean, nullable=False, server_default="true")
