from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.database.database import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    constructor_name = Column(String, nullable=False)
    base = Column(String)

    drivers = relationship("Driver", back_populates="team")
