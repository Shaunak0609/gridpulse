from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.database import Base


class Lap(Base):
    __tablename__ = "laps"

    id = Column(Integer, primary_key=True)

    # Link to our local sessions table. Required — every lap belongs to a session.
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)

    # OpenF1 identifies drivers by their race number, not an internal ID.
    # We store the raw number here and join to drivers.driver_number in queries.
    driver_number = Column(Integer, nullable=False)

    lap_number = Column(Integer, nullable=False)

    # Total lap time in seconds. Null when a lap was not completed (e.g. red flag,
    # in-lap, or the driver did not cross the timing line).
    lap_duration = Column(Float, nullable=True)

    duration_sector_1 = Column(Float, nullable=True)
    duration_sector_2 = Column(Float, nullable=True)
    duration_sector_3 = Column(Float, nullable=True)

    # True when this lap immediately follows a pit stop exit.
    # Pit-out laps have no valid sector 1 time and should be excluded from
    # fastest-lap calculations.
    is_pit_out_lap = Column(Boolean, nullable=False, default=False)

    # UTC timestamp when the lap started (crossing the start/finish line).
    date_start = Column(DateTime(timezone=True), nullable=True)

    session = relationship("Session", backref="laps")

    __table_args__ = (
        UniqueConstraint(
            "session_id", "driver_number", "lap_number",
            name="uq_lap_session_driver_lap",
        ),
    )
