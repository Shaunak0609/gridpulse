from sqlalchemy import Column, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.database import Base


class Stint(Base):
    __tablename__ = "stints"

    id = Column(Integer, primary_key=True)

    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    driver_number = Column(Integer, nullable=False)

    # Stint 1 is the driver's first run, stint 2 after their first pit stop, etc.
    stint_number = Column(Integer, nullable=True)

    # Tyre compound as reported by OpenF1.
    # Known values: SOFT, MEDIUM, HARD, INTERMEDIATE, WET
    compound = Column(String, nullable=True)

    # Lap on which this stint began and ended (inclusive on both ends).
    lap_start = Column(Integer, nullable=True)
    lap_end = Column(Integer, nullable=True)

    # How many laps the fitted tyre had already been used before this stint.
    # 0 means a brand-new tyre.
    tyre_age_at_start = Column(Integer, nullable=True)

    session = relationship("Session", backref="stints")

    __table_args__ = (
        UniqueConstraint(
            "session_id", "driver_number", "stint_number",
            name="uq_stint_session_driver_stint",
        ),
    )
