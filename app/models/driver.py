from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship

from app.database.database import Base


class Driver(Base):
    __tablename__ = "drivers"

    id = Column(Integer, primary_key=True)
    code = Column(String(3), nullable=False)
    full_name = Column(String, nullable=False)
    nationality = Column(String)
    driver_number = Column(Integer)
    team_id = Column(Integer, ForeignKey("teams.id"))

    team = relationship("Team", back_populates="drivers")
