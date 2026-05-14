from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.database import Base


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    race_id = Column(Integer, ForeignKey("races.id"), nullable=False)

    # e.g. "fp1", "fp2", "fp3", "sprint", "qualifying", "race"
    session_type = Column(String, nullable=False)

    # Human-readable label, e.g. "Practice 1", "Sprint", "Race"
    session_name = Column(String, nullable=False)

    start_time = Column(DateTime(timezone=True), nullable=True)
    end_time = Column(DateTime(timezone=True), nullable=True)

    # IANA timezone string from the data source, e.g. "Australia/Melbourne"
    timezone = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    race = relationship("Race", backref="sessions")

    __table_args__ = (
        UniqueConstraint("race_id", "session_type", name="uq_session_race_type"),
    )
