from sqlalchemy import Column, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship

from app.database.database import Base


class DriverStanding(Base):
    __tablename__ = "driver_standings"

    id = Column(Integer, primary_key=True)
    season = Column(Integer, nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id"))
    team_id = Column(Integer, ForeignKey("teams.id"))
    position = Column(Integer)
    points = Column(Float, default=0)
    wins = Column(Integer, default=0)
    podiums = Column(Integer, default=0)

    driver = relationship("Driver")
    team = relationship("Team")
