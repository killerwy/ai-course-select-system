from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from ._base import _uuid, _utcnow


class RecalculationRun(Base):
    __tablename__ = "recalculation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    trigger_type: Mapped[str] = mapped_column(String(30), nullable=False)
    course_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("courses.id", ondelete="SET NULL"), nullable=True)
    operator_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    idempotency_key: Mapped[str | None] = mapped_column(String(64), unique=True, nullable=True)
    summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    error_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    results: Mapped[list[RecalculationResult]] = relationship(back_populates="run", cascade="all, delete-orphan")


class RecalculationResult(Base):
    __tablename__ = "recalculation_results"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("recalculation_runs.id", ondelete="CASCADE"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(20), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(72), nullable=False)
    student_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    old_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(30), nullable=True)
    reason_code: Mapped[str] = mapped_column(String(50), nullable=False, default="OK")
    details_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)

    run: Mapped[RecalculationRun] = relationship(back_populates="results")

