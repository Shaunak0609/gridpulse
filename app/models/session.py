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

    # ── OpenF1 link fields ────────────────────────────────────────────────────
    # Populated by the OpenF1 sync script. NULL until the session is matched
    # and synced. All Phase 11 tables (laps, stints, etc.) reference this key.
    openf1_session_key = Column(Integer, nullable=True, unique=True)

    # The OpenF1 meeting (race weekend) key. Lets us fetch all sessions for a
    # meeting from OpenF1 without going through our races table.
    openf1_meeting_key = Column(Integer, nullable=True)

    # Short circuit name as OpenF1 reports it, e.g. "Monaco" or "Sakhir".
    # Complements the full circuit_name on the races table ("Circuit de Monaco").
    circuit_short_name = Column(String, nullable=True)

    # Country name as OpenF1 reports it. Avoids a join to races when building
    # the OpenF1 context in API responses.
    country_name = Column(String, nullable=True)

    race = relationship("Race", backref="sessions")

    __table_args__ = (
        UniqueConstraint("race_id", "session_type", name="uq_session_race_type"),
    )
