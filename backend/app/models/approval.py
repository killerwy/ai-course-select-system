from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ._base import _uuid, _utcnow


class ExceptionApproval(Base):
    __tablename__ = "exception_approvals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    request_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("enrollment_requests.id", ondelete="SET NULL"), nullable=True)
    enrollment_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("enrollments.id", ondelete="SET NULL"), nullable=True)
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    course_id: Mapped[str] = mapped_column(String(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING")
    rule_violations: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    reviewer_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    waived_rules: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_utcnow, onupdate=_utcnow)

