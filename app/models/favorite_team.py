from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.database import Base


class FavoriteTeam(Base):
    __tablename__ = "favorite_teams"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="favorite_teams")
    team = relationship("Team", backref="favorited_by")

    __table_args__ = (
        UniqueConstraint("user_id", "team_id", name="uq_favorite_team_user"),
    )
