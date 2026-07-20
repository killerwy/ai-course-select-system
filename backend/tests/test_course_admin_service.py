"""Tests for CourseMutationService."""

import pytest

from app.schemas.admin import RunStatus, TriggerType
from app.services.course_admin import CourseMutationService
from app.services.in_memory import InMemoryAdminRepository, InMemoryAuditWriter
from app.services.runs import RunRegistry


def build_mutation_service(*, course=None, enrollments=None, waitlists=None):
    repository = InMemoryAdminRepository(
        courses=[course or {"id": "course-201", "capacity": 1, "status": "OPEN", "version": 3, "schedules": []}],
        enrollments=enrollments,
        waitlists=waitlists,
    )
    audit_writer = InMemoryAuditWriter()
    registry = RunRegistry(id_factory=lambda: "run-mutation-001")
    service = CourseMutationService(repository=repository, run_registry=registry, audit_writer=audit_writer)
    return repository, audit_writer, registry, service


@pytest.mark.asyncio
async def test_expand_increments_capacity_and_creates_pending_run():
    """Expand increments capacity and creates a pending recalculation run."""
    repository, audit_writer, _, service = build_mutation_service()
    result = await service.expand(course_id="course-201", capacity_delta=2, operator_id="academic-001", idempotency_key="expand-001")
    assert result["course"]["capacity"] == 3
    assert result["course"]["version"] == 4
    assert result["run"].status == RunStatus.PENDING
    assert len(audit_writer.records) == 1


@pytest.mark.asyncio
async def test_reschedule_rejects_overlap_and_keeps_old_schedules():
    """Reschedule rejects overlapping schedules and keeps old ones."""
    repository, _, _, service = build_mutation_service(
        course={"id": "course-201", "capacity": 1, "status": "OPEN", "version": 3, "schedules": [{"weekday": 1, "start_minute": 480, "end_minute": 540, "room": "A101"}]}
    )
    with pytest.raises(ValueError, match="INVALID_SCHEDULE"):
        await service.reschedule(
            course_id="course-201",
            schedules=[
                {"weekday": 1, "start_minute": 600, "end_minute": 690, "room": "B201"},
                {"weekday": 1, "start_minute": 660, "end_minute": 720, "room": "B202"},
            ],
            operator_id="academic-001",
        )
    assert repository.courses["course-201"]["schedules"][0]["start_minute"] == 480


@pytest.mark.asyncio
async def test_cancel_closes_waitlist_and_marks_enrollments():
    """Cancel closes waitlist and marks enrollments as cancelled."""
    repository, audit_writer, _, service = build_mutation_service(
        course={"id": "course-201", "code": "AI201", "name": "人工智能导论", "capacity": 1, "status": "OPEN", "version": 3, "schedules": []},
        enrollments=[{"student_id": "student-001", "course_id": "course-201", "status": "ENROLLED"}],
        waitlists=[{"id": "wait-001", "student_id": "student-002", "course_id": "course-201", "status": "WAITING", "position": 1, "joined_at": "2026-07-16T06:00:00+00:00"}],
    )
    result = await service.cancel(course_id="course-201", reason="教室不可用", operator_id="academic-001", idempotency_key="cancel-001")
    assert result["course"]["status"] == "CANCELLED"
    assert repository.enrollments[("student-001", "course-201")]["status"] == "CANCELLED_BY_ADMIN"
    assert repository.waitlists["wait-001"]["status"] == "CLOSED"
    assert result["run"].status == RunStatus.SUCCEEDED
    student_audits = [record for record in audit_writer.records if record.action == "COURSE_DELETED_BY_TEACHER"]
    assert len(student_audits) == 2
    assert {record.subject_student_id for record in student_audits} == {"student-001", "student-002"}
    assert all(record.reason == "教师已删除课程《人工智能导论》" for record in student_audits)
    assert len(audit_writer.records) == 3


@pytest.mark.asyncio
async def test_invalid_capacity_reason_version_and_cancelled_course_are_rejected():
    """Invalid capacity, reason, version, and cancelled course are rejected."""
    repository, _, _, service = build_mutation_service()
    with pytest.raises(ValueError, match="INVALID_CAPACITY_DELTA"):
        await service.expand(course_id="course-201", capacity_delta=0, operator_id="academic-001")
    with pytest.raises(ValueError, match="EMPTY_REASON"):
        await service.cancel(course_id="course-201", reason=" ", operator_id="academic-001")
    with pytest.raises(ValueError, match="CONCURRENT_MODIFICATION"):
        await service.expand(course_id="course-201", capacity_delta=1, operator_id="academic-001", expected_version=99)
    repository.courses["course-201"]["status"] = "CANCELLED"
    with pytest.raises(ValueError, match="COURSE_ALREADY_CANCELLED"):
        await service.cancel(course_id="course-201", reason="重复操作", operator_id="academic-001")
