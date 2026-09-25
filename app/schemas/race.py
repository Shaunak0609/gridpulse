from pydantic import BaseModel


class PodiumEntry(BaseModel):
    position: int
    driver_name: str
    team_name: str | None


class RaceTeaser(BaseModel):
    """Quick result strip for a finished race — shown directly on its calendar card."""
    podium: list[PodiumEntry]
    fastest_lap_driver: str | None
    fastest_lap_time: float | None


class RaceSchema(BaseModel):
    id: int
    season: int
    round: int
    name: str
    circuit_name: str | None
    country: str | None
    start_date: str | None

    # Whether this race weekend includes a Sprint session.
    is_sprint_weekend: bool

    # "street" or "permanent" — see the CIRCUIT_TYPES lookup in
    # app/routes/calendar.py. Not sourced from any API; hand-maintained,
    # since neither Jolpica nor OpenF1 exposes a circuit classification.
    circuit_type: str

    # None until the race has both happened and had its official result
    # synced (see app/services/data_ingestion.py::sync_race_results).
    teaser: RaceTeaser | None
