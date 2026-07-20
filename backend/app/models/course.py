from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base
from ._base import _uuid


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    teacher_name: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    credits: Mapped[int] = mapped_column(Integer, nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    schedules: Mapped[list[CourseSchedule]] = relationship(back_populates="course", cascade="all, delete-orphan")
    prerequisites: Mapped[list[CoursePrerequisite]] = relationship(
        back_populates="course", cascade="all, delete-orphan", foreign_keys="CoursePrerequisite.course_id"
    )
    rules: Mapped[list[CourseRule]] = relationship(back_populates="course", cascade="all, delete-orphan")


class CourseSchedule(Base):
    __tablename__ = "course_schedules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    course_id: Mapped[str] = mapped_column(String(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    weekday: Mapped[int] = mapped_column(Integer, nullable=False)
    start_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    end_minute: Mapped[int] = mapped_column(Integer, nullable=False)
    room: Mapped[str] = mapped_column(String(50), nullable=False, default="TBD")

    course: Mapped[Course] = relationship(back_populates="schedules")


class CoursePrerequisite(Base):
    __tablename__ = "course_prerequisites"

    course_id: Mapped[str] = mapped_column(String(36), ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True)
    prerequisite_course_id: Mapped[str] = mapped_column(String(36), ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True)
    min_grade: Mapped[str] = mapped_column(String(5), nullable=False, default="D")

    course: Mapped[Course] = relationship(back_populates="prerequisites", foreign_keys=[course_id])


class CourseRule(Base):
    __tablename__ = "course_rules"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    course_id: Mapped[str] = mapped_column(String(36), ForeignKey("courses.id", ondelete="CASCADE"), nullable=False)
    rule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    course: Mapped[Course] = relationship(back_populates="rules")
