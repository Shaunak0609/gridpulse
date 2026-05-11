from sqlalchemy import Column, Integer, String, Date

from app.database.database import Base


class Race(Base):
    __tablename__ = "races"

    id = Column(Integer, primary_key=True)
    season = Column(Integer, nullable=False)
    round = Column(Integer, nullable=False)
    name = Column(String, nullable=False)
    circuit_name = Column(String)
    country = Column(String)
    start_date = Column(Date)
