from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..utils import ACTIVE_ENROLLMENT_STATUSES, schedules_overlap, validate_schedules


class CourseChangePreviewService:
    """Read-only estimate of the impact shown before a teacher changes a course."""

    def __init__(self, repository) -> None:
        self.repository = repository

    async def preview(
        self,
        *,
        course_id: str,
        operation: str,
        capacity: int | None = None,
        schedules: list[Mapping[str, Any]] | None = None,
    ) -> dict[str, Any]:
        course = await self.repository.get_course(course_id)
        if operation not in {"UPDATE", "EXPAND", "CANCEL"}:
            raise ValueError("INVALID_COURSE_OPERATION")
        proposed_schedules = [dict(item) for item in (schedules if schedules is not None else course.get("schedules", []))]
        validate_schedules(proposed_schedules)
        proposed_capacity = int(capacity if capacity is not None else course.get("capacity", 0))
        if proposed_capacity <= 0:
            raise ValueError("INVALID_CAPACITY_DELTA")

        target_enrollments = [
            item
            for item in await self.repository.list_enrollments(course_id)
            if item.get("status") in ACTIVE_ENROLLMENT_STATUSES
        ]
        waiting = await self.repository.list_waiting(course_id)
        if operation == "CANCEL":
            promoted = 0
            waiting_after = len(waiting)
        else:
            promoted = min(max(proposed_capacity - len(target_enrollments), 0), len(waiting))
            waiting_after = max(len(waiting) - promoted, 0)

        conflict_students: set[str] = set()
        if operation != "CANCEL" and schedules is not None:
            all_enrollments = list(self.repository.enrollments.values())
            for target in target_enrollments:
                student_id = str(target.get("student_id", ""))
                for other_enrollment in all_enrollments:
                    if (
                        str(other_enrollment.get("student_id", "")) != student_id
                        or str(other_enrollment.get("course_id", "")) == course_id
                        or other_enrollment.get("status") not in ACTIVE_ENROLLMENT_STATUSES
                    ):
                        continue
                    other_course = self.repository.courses.get(str(other_enrollment.get("course_id", "")))
                    if other_course and schedules_overlap(proposed_schedules, other_course.get("schedules", [])):
                        conflict_students.add(student_id)
                        break

        return {
            "operation": operation,
            "course_id": course_id,
            "course_code": str(course.get("code", course_id)),
            "course_name": str(course.get("name", course.get("code", course_id))),
            "enrolled_count": len(target_enrollments),
            "promoted": promoted,
            "waiting": waiting_after,
            "conflicts": len(conflict_students),
            "errors": 0,
        }
