from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.database import Base


class FavoriteDriver(Base):
    __tablename__ = "favorite_drivers"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    driver_id = Column(Integer, ForeignKey("drivers.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="favorite_drivers")
    driver = relationship("Driver", backref="favorited_by")

    __table_args__ = (
        UniqueConstraint("user_id", "driver_id", name="uq_favorite_driver_user"),
    )
