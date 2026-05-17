from datetime import datetime

from pydantic import BaseModel


class WeatherSampleResponse(BaseModel):
    id: int
    session_id: int
    date: datetime | None

    # Temperatures in degrees Celsius.
    air_temperature: float | None
    track_temperature: float | None

    # Humidity as a percentage (0–100).
    humidity: float | None

    # True when it is raining at the circuit.
    rainfall: bool | None

    # Wind speed in metres per second.
    wind_speed: float | None

    # Wind direction in degrees (0 = north, 90 = east, 180 = south, 270 = west).
    wind_direction: int | None

    model_config = {"from_attributes": True}
