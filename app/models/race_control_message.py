from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.database.database import Base


class RaceControlMessage(Base):
    __tablename__ = "race_control_messages"

    id = Column(Integer, primary_key=True)

    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)

    # UTC timestamp when the message was issued by race control.
    date = Column(DateTime(timezone=True), nullable=True)

    # Lap number on which the message was issued.
    lap_number = Column(Integer, nullable=True)

    # Broad category of the message.
    # Known values from OpenF1: SafetyCar, Flag, Drs, CarEvent, Other
    category = Column(String, nullable=True)

    # Full text of the race control message, e.g. "SAFETY CAR DEPLOYED".
    message = Column(Text, nullable=False)

    # Flag status associated with the message.
    # Known values: GREEN, YELLOW, DOUBLE YELLOW, RED, SC, VSC, CHEQUERED
    flag = Column(String, nullable=True)

    # Whether the message applies to the whole track, a sector, or a driver.
    # Known values: Track, Driver, Sector
    scope = Column(String, nullable=True)

    # Track sector number (1–3) when scope is "Sector". Null otherwise.
    sector = Column(Integer, nullable=True)

    # Driver number when the message targets a specific driver (e.g. a penalty).
    # Null for track-wide messages.
    driver_number = Column(Integer, nullable=True)

    session = relationship("Session", backref="race_control_messages")

    # No unique constraint — multiple messages can arrive on the same lap or
    # even the same timestamp in edge cases (e.g. simultaneous flag changes).
    # The ingestion script handles deduplication by clearing and reinserting
    # all messages for a session on each sync run.
