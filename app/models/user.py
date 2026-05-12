from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    username = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    timezone = Column(String, nullable=True, default="UTC")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
