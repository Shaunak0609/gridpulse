from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.database import Base


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    message = Column(String, nullable=True)
    read = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    related_race_id = Column(Integer, ForeignKey("races.id"), nullable=True)
    related_driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=True)

    user = relationship("User", backref="notifications")
    related_race = relationship("Race", backref="notifications")
    related_driver = relationship("Driver", backref="notifications")
