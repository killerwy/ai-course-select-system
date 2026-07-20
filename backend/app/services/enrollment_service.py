"""Enrollment and waitlist service for database mode."""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..contracts import Role
from ..domain.rules import (
    CompletedCourse,
    EnrollmentRecord,
    RuleEngine,
    ScheduleSlot,
    StudentProfile as RuleStudentProfile,
)
from ..models import (
    AuditLog,
    Course,
    Enrollment,
    EnrollmentRequest,
    ExceptionApproval,
    StudentProfile,
    WaitlistEntry,
)
from .audit import build_audit_record
from .course_query_service import _course, _course_input, course_summary
from ..utils import ACTIVE_ENROLLMENT_STATUSES, ALLOWED_WAIVED_RULES, _json_dump, _utcnow


ACTIVE_ENROLLMENT = ACTIVE_ENROLLMENT_STATUSES


async def check_enrollment(
    session: AsyncSession,
    student_id: str,
    course_id: str,
    *,
    waived_rules: set[str] | None = None,
    ignore_target_waitlist: bool = False,
) -> dict:
    course = await _course(session, course_id)
    if course is None:
        raise KeyError(course_id)
    enrollments = list(
        (await session.execute(select(Enrollment).where(Enrollment.student_id == student_id))).scalars().all()
    )
    course_ids = [item.course_id for item in enrollments if item.status in ACTIVE_ENROLLMENT and item.course_id != course_id]
    other_courses: list = []
    if course_ids:
        other_courses = list(
            (
                await session.execute(
                    select(Course).where(Course.id.in_(course_ids)).options(selectinload(Course.schedules))
                )
            ).scalars().unique().all()
        )
    profile = await session.get(StudentProfile, student_id)
    existing_waitlist = None
    if not ignore_target_waitlist:
        existing_waitlist = (
            await session.execute(
                select(WaitlistEntry).where(
                    WaitlistEntry.student_id == student_id,
                    WaitlistEntry.course_id == course_id,
                    WaitlistEntry.status == "WAITING",
                )
            )
        ).scalar_one_or_none()
    completed = [CompletedCourse(item.course_id, "A") for item in enrollments if item.status == "ENROLLED"]
    result = RuleEngine().check(
        course=_course_input(course),
        student_enrollments=[EnrollmentRecord(item.course_id, item.status) for item in enrollments if item.status in ACTIVE_ENROLLMENT],
        student_completed=completed,
        student_profile=RuleStudentProfile(grade=profile.grade if profile else 1, major=profile.major if profile else ""),
        request_type="ENROLL",
        enrolled_schedules=[
            ScheduleSlot(slot.weekday, slot.start_minute, slot.end_minute)
            for other in other_courses
            for slot in other.schedules
        ],
        existing_waitlist_for_course=existing_waitlist is not None,
        waived_rules=list(waived_rules or set()),
    )
    return result.to_dict()


async def _write_audit(
    session: AsyncSession,
    *,
    actor_id: str,
    actor_role: str,
    action: str,
    resource_type: str,
    resource_id: str,
    request_id: str,
    subject_student_id: str | None = None,
    before: dict | None = None,
    after: dict | None = None,
    reason: str | None = None,
    run_id: str | None = None,
) -> dict:
    record = build_audit_record(
        actor_id=actor_id,
        actor_role=Role(actor_role),
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        request_id=request_id,
        subject_student_id=subject_student_id,
        before_json=before,
        after_json=after,
        reason=reason,
        run_id=run_id,
    )
    session.add(
        AuditLog(
            id=record.id,
            actor_id=record.actor_id,
            subject_student_id=record.subject_student_id,
            actor_role=record.actor_role.value,
            action=record.action,
            resource_type=record.resource_type,
            resource_id=record.resource_id,
            before_json=_json_dump(record.before_json),
            after_json=_json_dump(record.after_json),
            reason=record.reason,
            run_id=record.run_id,
            request_id=record.request_id,
            created_at=record.created_at,
        )
    )
    await session.flush()
    return record.model_dump(mode="json")


async def _upsert_enrollment(session: AsyncSession, student_id: str, course_id: str, *, source: str) -> Enrollment:
    enrollment = (
        await session.execute(
            select(Enrollment).where(Enrollment.student_id == student_id, Enrollment.course_id == course_id).with_for_update()
        )
    ).scalar_one_or_none()
    now = _utcnow()
    if enrollment is None:
        enrollment = Enrollment(student_id=student_id, course_id=course_id, status="ENROLLED", source=source, created_at=now, updated_at=now)
        session.add(enrollment)
    else:
        enrollment.status = "ENROLLED"
        enrollment.source = source
        enrollment.updated_at = now
    await session.flush()
    return enrollment


async def process_enrollment_request(
    session: AsyncSession,
    *,
    student_id: str,
    course_id: str,
    request_type: str,
    idempotency_key: str | None,
    request_id: str,
) -> dict:
    if idempotency_key:
        existing = (
            await session.execute(select(EnrollmentRequest).where(EnrollmentRequest.idempotency_key == idempotency_key))
        ).scalar_one_or_none()
        if existing:
            return {"status": existing.reason or existing.status, "request_id": existing.id, "idempotent_replay": True}

    course = await _course(session, course_id, lock=True)
    if course is None:
        raise ValueError("COURSE_NOT_FOUND")
    course_snapshot = {"course_id": course.id, "course_code": course.code, "course_name": course.name}

    if request_type == "DROP":
        enrollment = (
            await session.execute(
                select(Enrollment).where(
                    Enrollment.student_id == student_id,
                    Enrollment.course_id == course_id,
                    Enrollment.status.in_(ACTIVE_ENROLLMENT),
                ).with_for_update()
            )
        ).scalar_one_or_none()
        waitlist = (
            await session.execute(
                select(WaitlistEntry).where(
                    WaitlistEntry.student_id == student_id,
                    WaitlistEntry.course_id == course_id,
                    WaitlistEntry.status == "WAITING",
                ).with_for_update()
            )
        ).scalar_one_or_none()
        target = enrollment or waitlist
        if target is None:
            raise ValueError("NO_RECORD_TO_DROP")
        old_status = target.status
        target.status = "DROPPED" if enrollment else "REMOVED"
        final_status = target.status
        resource_type = "enrollment" if enrollment else "waitlist_entry"
        await _write_audit(
            session,
            actor_id=student_id,
            actor_role="STUDENT",
            action="ENROLLMENT_DROPPED" if enrollment else "WAITLIST_REMOVED",
            resource_type=resource_type,
            resource_id=target.id,
            request_id=request_id,
            subject_student_id=student_id,
            before={**course_snapshot, "status": old_status},
            after={**course_snapshot, "status": final_status},
        )
    else:
        rule_result = await check_enrollment(session, student_id, course_id)
        if not rule_result["eligible"]:
            violations = [item["code"] for item in rule_result["violations"]]
            if violations and set(violations).issubset(ALLOWED_WAIVED_RULES):
                approval = ExceptionApproval(
                    student_id=student_id,
                    course_id=course_id,
                    status="PENDING",
                    rule_violations=_json_dump(violations),
                    waived_rules="[]",
                )
                session.add(approval)
            req = EnrollmentRequest(
                student_id=student_id,
                course_id=course_id,
                type=request_type,
                status="REJECTED",
                reason=rule_result["decision"],
                idempotency_key=idempotency_key,
            )
            session.add(req)
            await session.flush()
            return {"status": "REJECTED", "rule_result": rule_result, "request_id": req.id}

        occupied = (
            await session.execute(
                select(func.count()).select_from(Enrollment).where(
                    Enrollment.course_id == course_id,
                    Enrollment.status.in_(ACTIVE_ENROLLMENT),
                )
            )
        ).scalar_one()
        if request_type == "ENROLL" and occupied < course.capacity:
            enrollment = await _upsert_enrollment(session, student_id, course_id, source="DIRECT")
            final_status = "ENROLLED"
            target_id = enrollment.id
            action = "ENROLLMENT_CREATED"
            resource_type = "enrollment"
        else:
            current = (
                await session.execute(
                    select(WaitlistEntry).where(WaitlistEntry.student_id == student_id, WaitlistEntry.course_id == course_id).with_for_update()
                )
            ).scalar_one_or_none()
            waiting_count = (
                await session.execute(
                    select(func.count()).select_from(WaitlistEntry).where(
                        WaitlistEntry.course_id == course_id,
                        WaitlistEntry.status == "WAITING",
                    )
                )
            ).scalar_one()
            if current is None:
                current = WaitlistEntry(student_id=student_id, course_id=course_id, position=waiting_count + 1, status="WAITING")
                session.add(current)
            else:
                current.status = "WAITING"
                current.position = waiting_count + 1
                current.joined_at = _utcnow()
                current.skip_reason = None
            await session.flush()
            final_status = "WAITING"
            target_id = current.id
            action = "WAITLIST_JOINED"
            resource_type = "waitlist_entry"

        req = EnrollmentRequest(
            student_id=student_id,
            course_id=course_id,
            type=request_type,
            status="COMPLETED",
            reason=final_status,
            idempotency_key=idempotency_key,
        )
        session.add(req)
        await session.flush()
        await _write_audit(
            session,
            actor_id=student_id,
            actor_role="STUDENT",
            action=action,
            resource_type=resource_type,
            resource_id=target_id,
            request_id=request_id,
            subject_student_id=student_id,
            after={**course_snapshot, "status": final_status},
        )

    request = EnrollmentRequest(student_id=student_id, course_id=course_id, type=request_type, status="COMPLETED", reason=final_status, idempotency_key=idempotency_key)
    session.add(request)
    await session.flush()
    return {"status": final_status, "course_id": course_id, "request_id": request.id}


async def list_student_enrollments(session: AsyncSession, student_id: str) -> list[dict]:
    records = list(
        (await session.execute(select(Enrollment).where(Enrollment.student_id == student_id).order_by(Enrollment.created_at.desc(), Enrollment.id.desc()))).scalars().all()
    )
    return [
        {"id": item.id, "student_id": item.student_id, "course_id": item.course_id, "status": item.status, "source": item.source, "created_at": item.created_at.isoformat()}
        for item in records
    ]


async def list_student_waitlists(session: AsyncSession, student_id: str) -> list[dict]:
    records = list(
        (await session.execute(select(WaitlistEntry).where(WaitlistEntry.student_id == student_id).order_by(WaitlistEntry.joined_at.desc(), WaitlistEntry.id.desc()))).scalars().all()
    )
    return [
        {"id": item.id, "student_id": item.student_id, "course_id": item.course_id, "position": item.position, "status": item.status, "joined_at": item.joined_at.isoformat(), "skip_reason": item.skip_reason}
        for item in records
    ]


async def list_student_schedule(session: AsyncSession, student_id: str) -> dict:
    records = list(
        (
            await session.execute(
                select(Enrollment)
                .where(Enrollment.student_id == student_id, Enrollment.status.in_(ACTIVE_ENROLLMENT))
                .order_by(Enrollment.created_at, Enrollment.id)
            )
        ).scalars().all()
    )
    courses: list[dict] = []
    for enrollment in records:
        course = await _course(session, enrollment.course_id)
        if course is not None:
            courses.append(await course_summary(session, course))
    return {
        "courses": courses,
        "generated_at": _utcnow().isoformat(),
        "cache_backend": "database",
    }


async def list_student_audits(session: AsyncSession, student_id: str) -> list[dict]:
    records = list(
        (
            await session.execute(
                select(AuditLog).where(AuditLog.subject_student_id == student_id).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            )
        ).scalars().all()
    )
    return [
        {"id": item.id, "action": item.action, "resource_type": item.resource_type, "resource_id": item.resource_id, "reason": item.reason, "created_at": item.created_at.isoformat()}
        for item in records
    ]
