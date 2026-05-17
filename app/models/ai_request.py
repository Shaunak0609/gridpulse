from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database.database import Base


class AIRequest(Base):
    __tablename__ = "ai_requests"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=True)

    # Broad category used to understand what kinds of questions are being asked.
    # Expected values: "general", "driver_analysis", "race_summary", "strategy_explanation"
    request_type = Column(String, nullable=False, default="general")

    # Nullable — populated after the AI call completes.
    tokens_used = Column(Integer, nullable=True)
    model_name = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", backref="ai_requests")
