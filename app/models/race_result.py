from sqlalchemy import Column, Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.database import Base


class RaceResult(Base):
    __tablename__ = "race_results"

    id = Column(Integer, primary_key=True)

    # The "race"-type session for this round (see Session.session_type).
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)

    # Official classified finishing position from Jolpica.
    position = Column(Integer, nullable=True)

    # Raw Jolpica position text, e.g. "1", "R" (retired), "D" (disqualified).
    position_text = Column(String, nullable=True)

    # Official classification status, e.g. "Finished", "Disqualified", "Retired",
    # "+1 Lap", "Collision", "Engine". This is what GridPulse's lap-derived
    # finishing order (session_dashboard.py) cannot capture — penalties and DSQs.
    status = Column(String, nullable=True)

    grid = Column(Integer, nullable=True)
    points = Column(Float, nullable=True)
    laps = Column(Integer, nullable=True)

    # Gap to leader (e.g. "+8.481") or the leader's total race time. Null for
    # retirements/DSQs.
    finish_time = Column(String, nullable=True)

    session = relationship("Session", backref="race_results")
    driver = relationship("Driver")
    team = relationship("Team")

    __table_args__ = (
        UniqueConstraint("session_id", "driver_id", name="uq_race_result_session_driver"),
    )
