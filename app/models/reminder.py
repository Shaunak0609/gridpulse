from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.database import Base


class Reminder(Base):
    __tablename__ = "reminders"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    race_id = Column(Integer, ForeignKey("races.id"), nullable=True)
    title = Column(String, nullable=False)
    reminder_time = Column(DateTime(timezone=True), nullable=True)
    sent = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="reminders")
    race = relationship("Race", backref="reminders")
