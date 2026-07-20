"""Tests for CourseChangePreviewService."""

import pytest

from app.services.course_change_preview import CourseChangePreviewService
from app.services.in_memory import InMemoryAdminRepository


def build_service() -> CourseChangePreviewService:
    repository = InMemoryAdminRepository(
        courses=[
            {
                "id": "course-target",
                "code": "AI201",
                "name": "人工智能导论",
                "capacity": 2,
                "schedules": [{"weekday": 1, "start_minute": 480, "end_minute": 570, "room": "A101"}],
            },
            {
                "id": "course-other",
                "code": "CS101",
                "name": "程序设计基础",
                "capacity": 30,
                "schedules": [{"weekday": 2, "start_minute": 600, "end_minute": 690, "room": "B201"}],
            },
        ],
        enrollments=[
            {"student_id": "student-1", "course_id": "course-target", "status": "ENROLLED"},
            {"student_id": "student-2", "course_id": "course-target", "status": "ENROLLED"},
            {"student_id": "student-1", "course_id": "course-other", "status": "ENROLLED"},
        ],
        waitlists=[
            {"id": "wait-1", "student_id": "student-3", "course_id": "course-target", "status": "WAITING"},
            {"id": "wait-2", "student_id": "student-4", "course_id": "course-target", "status": "WAITING"},
        ],
    )
    return CourseChangePreviewService(repository)


@pytest.mark.asyncio
async def test_update_preview_counts_enrolled_waiting_promotions_and_time_conflicts():
    """Update preview counts enrolled, waiting, promotions, and time conflicts."""
    service = build_service()
    preview = await service.preview(
        course_id="course-target",
        operation="UPDATE",
        capacity=4,
        schedules=[{"weekday": 2, "start_minute": 620, "end_minute": 680, "room": "C301"}],
    )

    assert preview == {
        "operation": "UPDATE",
        "course_id": "course-target",
        "course_code": "AI201",
        "course_name": "人工智能导论",
        "enrolled_count": 2,
        "promoted": 2,
        "waiting": 0,
        "conflicts": 1,
        "errors": 0,
    }


@pytest.mark.asyncio
async def test_cancel_preview_reports_all_currently_waiting_students_as_affected():
    """Cancel preview reports all currently waiting students as affected."""
    service = build_service()
    preview = await service.preview(course_id="course-target", operation="CANCEL")

    assert preview["enrolled_count"] == 2
    assert preview["promoted"] == 0
    assert preview["waiting"] == 2
    assert preview["conflicts"] == 0


@pytest.mark.asyncio
async def test_preview_rejects_overlapping_schedules_within_the_same_course():
    """Preview rejects overlapping schedules within the same course."""
    service = build_service()
    with pytest.raises(ValueError, match="INVALID_SCHEDULE"):
        await service.preview(
            course_id="course-target",
            operation="UPDATE",
            schedules=[
                {"weekday": 3, "start_minute": 480, "end_minute": 570, "room": "A101"},
                {"weekday": 3, "start_minute": 540, "end_minute": 630, "room": "A102"},
            ],
        )
