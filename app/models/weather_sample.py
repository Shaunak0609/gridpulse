from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.database import Base


class WeatherSample(Base):
    __tablename__ = "weather_samples"

    id = Column(Integer, primary_key=True)

    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)

    # UTC timestamp of this weather reading. OpenF1 records weather roughly
    # every 60 seconds throughout a session.
    date = Column(DateTime(timezone=True), nullable=True)

    # Temperatures in degrees Celsius.
    air_temperature = Column(Float, nullable=True)
    track_temperature = Column(Float, nullable=True)

    # Humidity as a percentage (0–100).
    humidity = Column(Float, nullable=True)

    # True when it is raining at the circuit. The single most useful field
    # for race strategy and AI context ("was it a wet race?").
    rainfall = Column(Boolean, nullable=True)

    # Wind speed in metres per second.
    wind_speed = Column(Float, nullable=True)

    # Wind direction in degrees (0 = north, 90 = east, 180 = south, 270 = west).
    wind_direction = Column(Integer, nullable=True)

    session = relationship("Session", backref="weather_samples")

    __table_args__ = (
        UniqueConstraint(
            "session_id", "date",
            name="uq_weather_session_date",
        ),
    )
