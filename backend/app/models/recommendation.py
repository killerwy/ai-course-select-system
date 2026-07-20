from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from ._base import _uuid, _utcnow


class RecommendationSession(Base):
    __tablename__ = "recommendation_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    input_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    model: Mapped[str] = mapped_column(String(50), nullable=False, default="rule_fallback")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)

    items: Mapped[list[RecommendationItem]] = relationship(back_populates="session", cascade="all, delete-orphan")


class RecommendationItem(Base):
    __tablename__ = "recommendation_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), ForeignKey("recommendation_sessions.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[str] = mapped_column(String(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    reasons_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    uncertainties_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    eligibility_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    session: Mapped[RecommendationSession] = relationship(back_populates="items")

