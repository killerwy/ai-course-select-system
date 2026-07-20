"""Course query service for database mode."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..domain.rules import CourseInput, CourseRuleInput, Prerequisite, ScheduleSlot
from ..models import Course, Enrollment, WaitlistEntry
from ..utils import ACTIVE_ENROLLMENT_STATUSES, _json_load


ACTIVE_ENROLLMENT = ACTIVE_ENROLLMENT_STATUSES


async def _course(session: AsyncSession, course_id: str, *, lock: bool = False) -> Course | None:
    query = (
        select(Course)
        .where(Course.id == course_id)
        .options(selectinload(Course.schedules), selectinload(Course.prerequisites), selectinload(Course.rules))
    )
    if lock:
        query = query.with_for_update()
    return (await session.execute(query)).scalar_one_or_none()


async def course_summary(session: AsyncSession, course: Course) -> dict:
    enrolled_count = (
        await session.execute(
            select(func.count()).select_from(Enrollment).where(
                Enrollment.course_id == course.id,
                Enrollment.status.in_(ACTIVE_ENROLLMENT),
            )
        )
    ).scalar_one()
    waitlist_count = (
        await session.execute(
            select(func.count()).select_from(WaitlistEntry).where(
                WaitlistEntry.course_id == course.id,
                WaitlistEntry.status == "WAITING",
            )
        )
    ).scalar_one()
    return {
        "id": course.id,
        "code": course.code,
        "name": course.name,
        "teacher_name": course.teacher_name,
        "credits": course.credits,
        "capacity": course.capacity,
        "enrolled_count": enrolled_count,
        "waitlist_count": waitlist_count,
        "status": course.status,
        "version": course.version,
        "schedules": [
            {"weekday": item.weekday, "start_minute": item.start_minute, "end_minute": item.end_minute, "room": item.room}
            for item in sorted(course.schedules, key=lambda value: (value.weekday, value.start_minute, value.id))
        ],
        "prerequisites": [item.prerequisite_course_id for item in course.prerequisites],
    }


async def list_course_summaries(
    session: AsyncSession,
    *,
    keyword: str | None = None,
    status: str | None = None,
) -> list[dict]:
    query = select(Course).options(
        selectinload(Course.schedules), selectinload(Course.prerequisites), selectinload(Course.rules)
    )
    if status:
        query = query.where(Course.status == status)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.where(or_(Course.code.ilike(pattern), Course.name.ilike(pattern)))
    courses = list((await session.execute(query.order_by(Course.code, Course.id))).scalars().unique().all())
    return [await course_summary(session, course) for course in courses]


def _course_input(course: Course) -> CourseInput:
    return CourseInput(
        id=course.id,
        status=course.status,
        capacity=course.capacity,
        credits=course.credits,
        schedules=[ScheduleSlot(item.weekday, item.start_minute, item.end_minute) for item in course.schedules],
        prerequisites=[Prerequisite(item.prerequisite_course_id, item.min_grade) for item in course.prerequisites],
        rules=[
            CourseRuleInput(item.rule_type, _json_load(item.config_json, {}), item.enabled)
            for item in course.rules
        ],
    )
