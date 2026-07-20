"""MySQL-backed implementation of group C academic operations."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..models import (
    AuditLog,
    Course,
    CoursePrerequisite,
    CourseOperationApproval,
    CourseSchedule,
    Enrollment,
    ExceptionApproval,
    RecalculationResult as ResultModel,
    RecalculationRun as RunModel,
    WaitlistEntry,
)
from ..utils import ALLOWED_WAIVED_RULES, ACTIVE_ENROLLMENT_STATUSES, _utcnow
from .database_store import (
    _course,
    _json_dump,
    _json_load,
    _upsert_enrollment,
    _write_audit,
    check_enrollment,
    course_summary,
)
from .course_operation import decorate_courses_with_pending
from .course_change_preview import schedules_overlap, validate_schedules


def _run_error(code: str, message: str | None = None) -> ValueError:
    return ValueError(code if message is None else f"{code}:{message}")


async def _write_student_course_deleted_audit(
    session: AsyncSession,
    *,
    course: Course,
    student_id: str,
    resource_type: str,
    resource_id: str,
    old_status: str,
    new_status: str,
    operator_id: str,
    request_id: str,
    run_id: str,
) -> None:
    course_name = str(course.name or course.code or course.id)
    snapshot = {"course_id": course.id, "course_code": course.code, "course_name": course_name}
    await _write_audit(
        session,
        actor_id=operator_id,
        actor_role="ACADEMIC",
        subject_student_id=student_id,
        action="COURSE_DELETED_BY_TEACHER",
        resource_type=resource_type,
        resource_id=resource_id,
        request_id=f"{request_id}:student:{student_id}",
        before={**snapshot, "status": old_status},
        after={**snapshot, "status": new_status},
        reason=f"教师已删除课程《{course_name}》",
        run_id=run_id,
    )


class DatabaseAdminService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def preview_course_change(
        self,
        *,
        course_id: str,
        operation: str,
        capacity: int | None = None,
        schedules: list[dict] | None = None,
    ) -> dict:
        if operation not in {"UPDATE", "EXPAND", "CANCEL"}:
            raise _run_error("INVALID_COURSE_OPERATION")
        course = await _course(self.session, course_id)
        if course is None:
            raise _run_error("COURSE_NOT_FOUND")
        proposed_schedules = schedules if schedules is not None else [
            {"weekday": item.weekday, "start_minute": item.start_minute, "end_minute": item.end_minute, "room": item.room}
            for item in course.schedules
        ]
        validate_schedules(proposed_schedules)
        proposed_capacity = int(capacity if capacity is not None else course.capacity)
        if proposed_capacity <= 0:
            raise _run_error("INVALID_CAPACITY_DELTA")

        target_enrollments = list((await self.session.execute(
            select(Enrollment).where(Enrollment.course_id == course_id, Enrollment.status.in_(ACTIVE_ENROLLMENT_STATUSES))
        )).scalars().all())
        waiting_count = int((await self.session.execute(
            select(func.count()).select_from(WaitlistEntry).where(
                WaitlistEntry.course_id == course_id,
                WaitlistEntry.status == "WAITING",
            )
        )).scalar_one())
        if operation == "CANCEL":
            promoted = 0
            waiting_after = waiting_count
        else:
            promoted = min(max(proposed_capacity - len(target_enrollments), 0), waiting_count)
            waiting_after = max(waiting_count - promoted, 0)

        conflict_students: set[str] = set()
        if operation != "CANCEL" and schedules is not None and target_enrollments:
            student_ids = [item.student_id for item in target_enrollments]
            other_enrollments = list((await self.session.execute(
                select(Enrollment).where(
                    Enrollment.student_id.in_(student_ids),
                    Enrollment.course_id != course_id,
                    Enrollment.status.in_(ACTIVE_ENROLLMENT_STATUSES),
                )
            )).scalars().all())
            other_course_ids = {item.course_id for item in other_enrollments}
            other_courses = {}
            if other_course_ids:
                records = list((await self.session.execute(
                    select(Course).options(selectinload(Course.schedules)).where(Course.id.in_(other_course_ids))
                )).scalars().all())
                other_courses = {item.id: item for item in records}
            for enrollment in other_enrollments:
                other_course = other_courses.get(enrollment.course_id)
                other_schedules = [] if other_course is None else [
                    {"weekday": item.weekday, "start_minute": item.start_minute, "end_minute": item.end_minute}
                    for item in other_course.schedules
                ]
                if schedules_overlap(proposed_schedules, other_schedules):
                    conflict_students.add(enrollment.student_id)

        return {
            "operation": operation,
            "course_id": course_id,
            "course_code": course.code,
            "course_name": course.name,
            "enrolled_count": len(target_enrollments),
            "promoted": promoted,
            "waiting": waiting_after,
            "conflicts": len(conflict_students),
            "errors": 0,
        }

    async def submit_course_operation(
        self,
        *,
        operation: str,
        course_id: str | None,
        payload: dict,
        requester_id: str,
        request_id: str,
        idempotency_key: str | None,
    ) -> dict:
        if idempotency_key:
            existing = (await self.session.execute(select(CourseOperationApproval).where(CourseOperationApproval.idempotency_key == idempotency_key))).scalar_one_or_none()
            if existing is not None:
                return {"operation": self._operation_payload(existing), "reused": True}
        normalized = dict(payload)
        normalized["schedules"] = [dict(item) for item in payload.get("schedules", [])]
        normalized["prerequisites"] = list(payload.get("prerequisites") or [])
        if operation == "CREATE":
            code = str(normalized.get("code", "")).strip()
            if not code or not str(normalized.get("name", "")).strip() or not str(normalized.get("teacher_name", "")).strip():
                raise _run_error("INVALID_COURSE")
            self._validate_schedules(normalized["schedules"])
            duplicate = (await self.session.execute(select(Course).where(Course.code == code))).scalar_one_or_none()
            if duplicate is not None:
                raise _run_error("COURSE_ALREADY_EXISTS")
            pending_creates = list((await self.session.execute(select(CourseOperationApproval).where(CourseOperationApproval.operation == "CREATE", CourseOperationApproval.status == "PENDING"))).scalars().all())
            if any(str(_json_load(item.payload_json, {}).get("code", "")).strip() == code for item in pending_creates):
                raise _run_error("COURSE_OPERATION_PENDING")
            await self._resolve_prerequisites(normalized["prerequisites"])
            course_id = None
        elif operation == "UPDATE":
            course = await _course(self.session, str(course_id), lock=True)
            if course is None:
                raise _run_error("COURSE_NOT_FOUND")
            if course.status == "CANCELLED":
                raise _run_error("COURSE_CANCELLED")
            expected_version = normalized.get("expected_version")
            if expected_version is not None and course.version != expected_version:
                raise _run_error("CONCURRENT_MODIFICATION")
            code = str(normalized.get("code", "")).strip()
            if not code or not str(normalized.get("name", "")).strip() or not str(normalized.get("teacher_name", "")).strip():
                raise _run_error("INVALID_COURSE")
            self._validate_schedules(normalized["schedules"])
            duplicate = (await self.session.execute(select(Course).where(Course.code == code, Course.id != course_id))).scalar_one_or_none()
            if duplicate is not None:
                raise _run_error("COURSE_ALREADY_EXISTS")
            await self._resolve_prerequisites(normalized["prerequisites"], course_id=course_id)
            active = (await self.session.execute(
                select(CourseOperationApproval).where(
                    CourseOperationApproval.status == "PENDING",
                    CourseOperationApproval.course_id == course_id,
                )
            )).scalar_one_or_none()
            if active is not None:
                raise _run_error("COURSE_OPERATION_PENDING")
        elif operation == "CANCEL":
            course = await _course(self.session, str(course_id), lock=True)
            if course is None:
                raise _run_error("COURSE_NOT_FOUND")
            if not str(normalized.get("reason", "")).strip():
                raise _run_error("EMPTY_REASON")
            expected_version = normalized.get("expected_version")
            if expected_version is not None and course.version != expected_version:
                raise _run_error("CONCURRENT_MODIFICATION")
            normalized["code"] = course.code
            normalized["name"] = course.name
            active = (await self.session.execute(
                select(CourseOperationApproval).where(
                    CourseOperationApproval.status == "PENDING",
                    CourseOperationApproval.course_id == course_id,
                )
            )).scalar_one_or_none()
            if active is not None:
                raise _run_error("COURSE_OPERATION_PENDING")
        else:
            raise _run_error("INVALID_COURSE_OPERATION")
        record = CourseOperationApproval(
            operation=operation,
            course_id=course_id,
            requester_id=requester_id,
            status="PENDING",
            payload_json=_json_dump(normalized),
            reason=normalized.get("reason"),
            idempotency_key=idempotency_key,
        )
        self.session.add(record)
        await self.session.flush()
        await _write_audit(self.session, actor_id=requester_id, actor_role="ACADEMIC", action="COURSE_OPERATION_SUBMITTED", resource_type="course_operation", resource_id=record.id, request_id=request_id, after=self._operation_payload(record), reason="course operation submitted")
        return {"operation": self._operation_payload(record), "reused": False}

    async def list_course_operations(self, *, status: str | None = None, course_id: str | None = None) -> list[dict]:
        query = select(CourseOperationApproval).order_by(CourseOperationApproval.created_at.desc(), CourseOperationApproval.id.desc())
        if status:
            query = query.where(CourseOperationApproval.status == status)
        if course_id:
            query = query.where(CourseOperationApproval.course_id == course_id)
        rows = list((await self.session.execute(query)).scalars().all())
        return [self._operation_payload(item) for item in rows]

    async def decide_course_operation(self, *, operation_id: str, decision: str, comment: str, reviewer_id: str, request_id: str) -> dict:
        if not comment.strip():
            raise _run_error("EMPTY_COMMENT")
        operation = (await self.session.execute(select(CourseOperationApproval).where(CourseOperationApproval.id == operation_id).with_for_update())).scalar_one_or_none()
        if operation is None:
            raise _run_error("COURSE_OPERATION_NOT_FOUND")
        if operation.status != "PENDING":
            raise _run_error("COURSE_OPERATION_NOT_PENDING")
        if decision == "REJECT":
            operation.status = "REJECTED"
            operation.reviewer_id = reviewer_id
            operation.comment = comment
            await self.session.flush()
            await _write_audit(self.session, actor_id=reviewer_id, actor_role="ACADEMIC", action="COURSE_OPERATION_REJECTED", resource_type="course_operation", resource_id=operation.id, request_id=request_id, after=self._operation_payload(operation), reason=comment)
            return {"operation": self._operation_payload(operation), "course": await self._operation_course(operation), "run": None, "reused": False}
        payload = _json_load(operation.payload_json, {})
        if operation.operation == "CREATE":
            result = await self.create_course(operator_id=reviewer_id, request_id=request_id, **payload)
            operation.course_id = result["course"]["id"]
        elif operation.operation == "UPDATE":
            result = await self.update_course_details(course_id=operation.course_id or "", operator_id=reviewer_id, request_id=request_id, idempotency_key=f"operation-update-{operation.id}", expected_version=payload.pop("expected_version", None), **payload)
        elif operation.operation == "CANCEL":
            result = await self.delete_course(course_id=operation.course_id or "", operator_id=reviewer_id, request_id=request_id, reason=payload.get("reason", ""), idempotency_key=f"operation-cancel-{operation.id}", expected_version=payload.get("expected_version"))
        else:
            raise _run_error("INVALID_COURSE_OPERATION")
        operation.status = "APPROVED"
        operation.reviewer_id = reviewer_id
        operation.comment = comment
        await self.session.flush()
        await _write_audit(self.session, actor_id=reviewer_id, actor_role="ACADEMIC", action="COURSE_OPERATION_APPROVED", resource_type="course_operation", resource_id=operation.id, request_id=request_id, after=self._operation_payload(operation), reason=comment, run_id=(result.get("run") or {}).get("id") if isinstance(result.get("run"), dict) else getattr(result.get("run"), "id", None))
        return {"operation": self._operation_payload(operation), "course": result.get("course"), "run": result.get("run"), "reused": result.get("reused", False)}

    async def _operation_course(self, operation: CourseOperationApproval) -> dict | None:
        if not operation.course_id:
            return None
        course = await _course(self.session, operation.course_id)
        return await course_summary(self.session, course) if course is not None else None

    @staticmethod
    def _operation_payload(operation: CourseOperationApproval) -> dict:
        return {
            "id": operation.id,
            "operation": operation.operation,
            "course_id": operation.course_id,
            "requester_id": operation.requester_id,
            "reviewer_id": operation.reviewer_id,
            "status": operation.status,
            "payload": _json_load(operation.payload_json, {}),
            "reason": operation.reason,
            "comment": operation.comment,
            "idempotency_key": operation.idempotency_key,
            "created_at": operation.created_at.isoformat() if operation.created_at else None,
            "updated_at": operation.updated_at.isoformat() if operation.updated_at else None,
        }

    async def create_course(
        self,
        *,
        code: str,
        name: str,
        teacher_name: str,
        credits: int,
        capacity: int,
        schedules: list[dict],
        prerequisites: list[str],
        operator_id: str,
        request_id: str,
    ) -> dict:
        code = code.strip()
        name = name.strip()
        teacher_name = teacher_name.strip()
        if not code or not name or not teacher_name or credits <= 0 or capacity <= 0:
            raise _run_error("INVALID_COURSE")
        self._validate_schedules(schedules)
        duplicate = (await self.session.execute(select(Course).where(Course.code == code))).scalar_one_or_none()
        if duplicate is not None:
            raise _run_error("COURSE_ALREADY_EXISTS")
        prerequisite_ids = await self._resolve_prerequisites(prerequisites)
        course = Course(id=str(uuid4()), code=code, name=name, teacher_name=teacher_name, credits=credits, capacity=capacity, status="OPEN", version=1)
        self.session.add(course)
        await self.session.flush()
        for item in schedules:
            self.session.add(CourseSchedule(course_id=course.id, **item))
        for prerequisite_course_id in prerequisite_ids:
            self.session.add(CoursePrerequisite(course_id=course.id, prerequisite_course_id=prerequisite_course_id, min_grade="D"))
        await self.session.flush()
        saved = await _course(self.session, course.id)
        summary = await course_summary(self.session, saved)
        await _write_audit(
            self.session,
            actor_id=operator_id,
            actor_role="ACADEMIC",
            action="COURSE_CREATED",
            resource_type="course",
            resource_id=course.id,
            request_id=request_id,
            before={},
            after=summary,
            reason="course created",
        )
        return {"course": summary, "run": None, "reused": False}

    async def update_course_details(
        self,
        *,
        course_id: str,
        code: str,
        name: str,
        teacher_name: str,
        credits: int,
        capacity: int,
        schedules: list[dict],
        prerequisites: list[str],
        operator_id: str,
        request_id: str,
        idempotency_key: str | None,
        expected_version: int | None,
    ) -> dict:
        code = code.strip()
        name = name.strip()
        teacher_name = teacher_name.strip()
        if not code or not name or not teacher_name or credits <= 0 or capacity <= 0:
            raise _run_error("INVALID_COURSE")
        self._validate_schedules(schedules)
        course = await _course(self.session, course_id, lock=True)
        if course is None:
            raise _run_error("COURSE_NOT_FOUND")
        if expected_version is not None and course.version != expected_version:
            raise _run_error("CONCURRENT_MODIFICATION")
        if course.status == "CANCELLED":
            raise _run_error("COURSE_CANCELLED")
        duplicate = (await self.session.execute(select(Course).where(Course.code == code, Course.id != course_id))).scalar_one_or_none()
        if duplicate is not None:
            raise _run_error("COURSE_ALREADY_EXISTS")
        prerequisite_ids = await self._resolve_prerequisites(prerequisites, course_id=course_id)
        before = await course_summary(self.session, course)
        schedules_changed = [
            (item.weekday, item.start_minute, item.end_minute, item.room)
            for item in sorted(course.schedules, key=lambda value: value.id)
        ] != [
            (item["weekday"], item["start_minute"], item["end_minute"], item["room"])
            for item in schedules
        ]
        capacity_changed = course.capacity != capacity
        course.code = code
        course.name = name
        course.teacher_name = teacher_name
        course.credits = credits
        course.capacity = capacity
        course.version += 1
        for old in list(course.schedules):
            await self.session.delete(old)
        await self.session.flush()
        for item in schedules:
            self.session.add(CourseSchedule(course_id=course.id, **item))
        for old in list(course.prerequisites):
            await self.session.delete(old)
        await self.session.flush()
        for prerequisite_course_id in prerequisite_ids:
            self.session.add(CoursePrerequisite(course_id=course.id, prerequisite_course_id=prerequisite_course_id, min_grade="D"))
        await self.session.flush()
        run = None
        if capacity_changed or schedules_changed:
            run, reused = await self._create_run(course_id=course_id, trigger_type="COURSE_UPDATE", operator_id=operator_id, idempotency_key=idempotency_key)
            if not reused:
                await self.execute_run(run["id"])
            run = await self._run(run["id"])
        saved = await _course(self.session, course_id)
        after = await course_summary(self.session, saved)
        await _write_audit(
            self.session,
            actor_id=operator_id,
            actor_role="ACADEMIC",
            action="COURSE_UPDATED",
            resource_type="course",
            resource_id=course_id,
            request_id=request_id,
            before=before,
            after=after,
            reason="course details updated",
            run_id=run["id"] if run else None,
        )
        return {"course": after, "run": run, "reused": False}

    async def _resolve_prerequisites(self, values: list[str], *, course_id: str | None = None) -> list[str]:
        """Accept the UI's course codes while persisting prerequisite IDs.

        The relational table stores ``courses.id`` in its foreign-key column,
        whereas the admin form asks for a human-facing course code such as
        ``AI201``. Existing API clients that already send IDs remain supported.
        """
        normalized = []
        for value in values or []:
            item = str(value).strip()
            if item and item not in normalized:
                normalized.append(item)
        if not normalized:
            return []
        lowered_codes = [item.casefold() for item in normalized]
        rows = list(
            (
                await self.session.execute(
                    select(Course).where(
                        or_(
                            Course.id.in_(normalized),
                            func.lower(Course.code).in_(lowered_codes),
                        )
                    )
                )
            ).scalars().all()
        )
        by_id = {str(row.id): row for row in rows}
        by_code = {str(row.code).casefold(): row for row in rows}
        resolved: list[str] = []
        for item in normalized:
            prerequisite = by_id.get(item) or by_code.get(item.casefold())
            if prerequisite is None:
                raise _run_error("PREREQUISITE_NOT_FOUND")
            if course_id and prerequisite.id == course_id:
                raise _run_error("INVALID_COURSE")
            if prerequisite.id not in resolved:
                resolved.append(prerequisite.id)
        return resolved

    async def list_courses(self, *, status: str | None = None, keyword: str | None = None) -> list[dict]:
        query = select(Course).options(selectinload(Course.schedules), selectinload(Course.prerequisites), selectinload(Course.rules)).order_by(Course.code, Course.id)
        if status and status != "PENDING_APPROVAL":
            query = query.where(Course.status == status)
        if keyword:
            pattern = f"%{keyword.strip()}%"
            query = query.where(Course.code.ilike(pattern) | Course.name.ilike(pattern))
        courses = list((await self.session.execute(query)).scalars().unique().all())
        values = [await course_summary(self.session, item) for item in courses]
        operations = await self.list_course_operations(status="PENDING")
        values = decorate_courses_with_pending(values, operations)
        if keyword:
            needle = keyword.strip().casefold()
            values = [item for item in values if needle in f"{item.get('code', '')} {item.get('name', '')}".casefold()]
        if status:
            values = [item for item in values if item.get("status") == status]
        return values

    async def delete_course(self, *, course_id: str, operator_id: str, request_id: str, reason: str, idempotency_key: str | None = None, expected_version: int | None = None) -> dict:
        if not reason.strip():
            raise _run_error("EMPTY_REASON")
        course = await _course(self.session, course_id, lock=True)
        if course is None:
            raise _run_error("COURSE_NOT_FOUND")
        if expected_version is not None and course.version != expected_version:
            raise _run_error("CONCURRENT_MODIFICATION")
        before = await course_summary(self.session, course)
        run, reused = await self._create_run(course_id=course_id, trigger_type="CANCEL", operator_id=operator_id, idempotency_key=idempotency_key)
        if reused:
            return {"course": None, "run": run, "reused": True}
        results: list[dict] = []
        enrollments = list((await self.session.execute(select(Enrollment).where(Enrollment.course_id == course_id).with_for_update())).scalars().all())
        for item in enrollments:
            if item.status in ACTIVE_ENROLLMENT_STATUSES:
                old = item.status
                item.status = "CANCELLED_BY_ADMIN"
                results.append({"entity_type": "ENROLLMENT", "entity_id": item.id, "student_id": item.student_id, "old_status": old, "new_status": item.status, "reason_code": "COURSE_CANCELLED", "details": {}})
                await _write_student_course_deleted_audit(self.session, course=course, student_id=item.student_id, resource_type="enrollment", resource_id=item.id, old_status=old, new_status=item.status, operator_id=operator_id, request_id=request_id, run_id=run["id"])
        waitlists = list((await self.session.execute(select(WaitlistEntry).where(WaitlistEntry.course_id == course_id).with_for_update())).scalars().all())
        for item in waitlists:
            if item.status == "WAITING":
                item.status = "CLOSED"
                results.append({"entity_type": "WAITLIST", "entity_id": item.id, "student_id": item.student_id, "old_status": "WAITING", "new_status": "CLOSED", "reason_code": "COURSE_CANCELLED", "details": {}})
                await _write_student_course_deleted_audit(self.session, course=course, student_id=item.student_id, resource_type="waitlist_entry", resource_id=item.id, old_status="WAITING", new_status="CLOSED", operator_id=operator_id, request_id=request_id, run_id=run["id"])
        await self._finish_run(run["id"], results=results, checked=len(results))
        await _write_audit(self.session, actor_id=operator_id, actor_role="ACADEMIC", action="COURSE_DELETED", resource_type="course", resource_id=course_id, request_id=request_id, before=before, after={"id": course_id, "status": "DELETED"}, reason=reason, run_id=run["id"])
        await self.session.delete(course)
        await self.session.flush()
        return {"course": None, "run": await self._run(run["id"]), "reused": False}

    async def _run(self, run_id: str) -> dict:
        query = select(RunModel).where(RunModel.id == run_id).options(selectinload(RunModel.results))
        run = (await self.session.execute(query)).scalar_one_or_none()
        if run is None:
            raise _run_error("RUN_NOT_FOUND")
        summary = _json_load(run.summary_json, {})
        return {
            "id": run.id,
            "course_id": run.course_id,
            "trigger_type": run.trigger_type,
            "operator_id": run.operator_id,
            "status": run.status,
            "summary": summary,
            "results": [
                {
                    "entity_type": item.entity_type,
                    "entity_id": item.entity_id,
                    "student_id": item.student_id,
                    "old_status": item.old_status,
                    "new_status": item.new_status,
                    "reason_code": item.reason_code,
                    "details": _json_load(item.details_json, {}),
                    "occurred_at": item.occurred_at.isoformat() if item.occurred_at else None,
                }
                for item in sorted(run.results, key=lambda value: (value.occurred_at or datetime.min.replace(tzinfo=timezone.utc), value.id))
            ],
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "error": _json_load(run.error_json, None),
        }

    async def get_run(self, run_id: str) -> dict:
        return await self._run(run_id)

    async def _create_run(self, *, course_id: str, trigger_type: str, operator_id: str, idempotency_key: str | None) -> tuple[dict, bool]:
        if idempotency_key:
            existing = (
                await self.session.execute(select(RunModel).where(RunModel.idempotency_key == idempotency_key))
            ).scalar_one_or_none()
            if existing:
                return await self._run(existing.id), True
        active = (
            await self.session.execute(
                select(RunModel).where(RunModel.course_id == course_id, RunModel.status.in_(["PENDING", "RUNNING"]))
            )
        ).scalar_one_or_none()
        if active:
            raise _run_error("RUN_ALREADY_ACTIVE")
        run = RunModel(
            trigger_type=trigger_type,
            course_id=course_id,
            operator_id=operator_id,
            status="PENDING",
            idempotency_key=idempotency_key,
            summary_json=_json_dump({"checked": 0, "promoted": 0, "skipped": 0, "conflicts": 0, "waiting": 0, "errors": 0}),
        )
        self.session.add(run)
        await self.session.flush()
        return await self._run(run.id), False

    async def mutate_course(
        self,
        *,
        course_id: str,
        operation: str,
        operator_id: str,
        request_id: str,
        idempotency_key: str | None,
        expected_version: int | None,
        capacity_delta: int | None = None,
        schedules: list[dict] | None = None,
        reason: str | None = None,
    ) -> dict:
        course = await _course(self.session, course_id, lock=True)
        if course is None:
            raise _run_error("COURSE_NOT_FOUND")
        if expected_version is not None and course.version != expected_version:
            raise _run_error("CONCURRENT_MODIFICATION")
        if course.status == "CANCELLED":
            raise _run_error("COURSE_CANCELLED")
        if operation == "EXPAND":
            if not capacity_delta or capacity_delta <= 0:
                raise _run_error("INVALID_CAPACITY_DELTA")
        if operation == "RESCHEDULE":
            self._validate_schedules(schedules or [])
        if operation == "CANCEL" and not (reason or "").strip():
            raise _run_error("EMPTY_REASON")

        run, reused = await self._create_run(course_id=course_id, trigger_type=operation, operator_id=operator_id, idempotency_key=idempotency_key)
        if reused:
            return {"course": await course_summary(self.session, course), "run": run, "reused": True}

        before = await course_summary(self.session, course)
        if operation == "EXPAND":
            course.capacity += int(capacity_delta or 0)
            action = "COURSE_EXPANDED"
            audit_reason = f"capacity +{capacity_delta}"
        elif operation == "RESCHEDULE":
            for old in list(course.schedules):
                await self.session.delete(old)
            await self.session.flush()
            for item in schedules or []:
                self.session.add(CourseSchedule(course_id=course.id, **item))
            action = "COURSE_RESCHEDULED"
            audit_reason = "course schedules changed"
        else:
            course.status = "CANCELLED"
            action = "COURSE_CANCELLED"
            audit_reason = reason
        course.version += 1
        await self.session.flush()

        if operation == "CANCEL":
            results: list[dict] = []
            enrollments = list((await self.session.execute(select(Enrollment).where(Enrollment.course_id == course_id).with_for_update())).scalars().all())
            for item in enrollments:
                if item.status in ACTIVE_ENROLLMENT_STATUSES:
                    old = item.status
                    item.status = "CANCELLED_BY_ADMIN"
                    results.append({"entity_type": "ENROLLMENT", "entity_id": item.id, "student_id": item.student_id, "old_status": old, "new_status": item.status, "reason_code": "COURSE_CANCELLED", "details": {}})
                    await _write_student_course_deleted_audit(self.session, course=course, student_id=item.student_id, resource_type="enrollment", resource_id=item.id, old_status=old, new_status=item.status, operator_id=operator_id, request_id=request_id, run_id=run["id"])
            waitlists = list((await self.session.execute(select(WaitlistEntry).where(WaitlistEntry.course_id == course_id, WaitlistEntry.status == "WAITING").with_for_update())).scalars().all())
            for item in waitlists:
                item.status = "CLOSED"
                results.append({"entity_type": "WAITLIST", "entity_id": item.id, "student_id": item.student_id, "old_status": "WAITING", "new_status": "CLOSED", "reason_code": "COURSE_CANCELLED", "details": {}})
                await _write_student_course_deleted_audit(self.session, course=course, student_id=item.student_id, resource_type="waitlist_entry", resource_id=item.id, old_status="WAITING", new_status="CLOSED", operator_id=operator_id, request_id=request_id, run_id=run["id"])
            await self._finish_run(run["id"], results=results, checked=len(results))
        else:
            await self.execute_run(run["id"])

        updated_course = await _course(self.session, course_id)
        await _write_audit(
            self.session,
            actor_id=operator_id,
            actor_role="ACADEMIC",
            action=action,
            resource_type="course",
            resource_id=course_id,
            request_id=request_id,
            before=before,
            after=await course_summary(self.session, updated_course),
            reason=audit_reason,
            run_id=run["id"],
        )
        return {"course": await course_summary(self.session, updated_course), "run": await self._run(run["id"]), "reused": False}

    async def recalculate(self, *, course_id: str, operator_id: str, request_id: str, idempotency_key: str | None, expected_version: int | None) -> dict:
        course = await _course(self.session, course_id, lock=True)
        if course is None:
            raise _run_error("COURSE_NOT_FOUND")
        if expected_version is not None and course.version != expected_version:
            raise _run_error("CONCURRENT_MODIFICATION")
        run, reused = await self._create_run(course_id=course_id, trigger_type="MANUAL", operator_id=operator_id, idempotency_key=idempotency_key)
        if not reused:
            await _write_audit(self.session, actor_id=operator_id, actor_role="ACADEMIC", action="RECALCULATION_STARTED", resource_type="recalculation_run", resource_id=run["id"], request_id=request_id, run_id=run["id"])
            await self.execute_run(run["id"])
        return {"run": await self._run(run["id"]), "reused": reused}

    async def execute_run(self, run_id: str) -> dict:
        run_model = (await self.session.execute(select(RunModel).where(RunModel.id == run_id).with_for_update())).scalar_one_or_none()
        if run_model is None:
            raise _run_error("RUN_NOT_FOUND")
        run_model.status = "RUNNING"
        run_model.started_at = _utcnow()
        await self.session.flush()
        try:
            course = await _course(self.session, run_model.course_id or "", lock=True)
            if course is None:
                raise _run_error("COURSE_NOT_FOUND")
            if course.status == "CANCELLED":
                raise _run_error("COURSE_CANCELLED")
            course_snapshot = {"course_id": course.id, "course_code": course.code, "course_name": course.name}
            enrollments = list((await self.session.execute(select(Enrollment).where(Enrollment.course_id == course.id).with_for_update())).scalars().all())
            waiting = list((await self.session.execute(select(WaitlistEntry).where(WaitlistEntry.course_id == course.id, WaitlistEntry.status == "WAITING").order_by(WaitlistEntry.joined_at, WaitlistEntry.id).with_for_update())).scalars().all())
            occupied = sum(1 for item in enrollments if item.status in ACTIVE_ENROLLMENT_STATUSES)
            available = max(course.capacity - occupied, 0)
            results: list[dict] = []
            promoted = skipped = conflicts = 0
            for entry in waiting:
                rule = await check_enrollment(self.session, entry.student_id, course.id, ignore_target_waitlist=True)
                blocker = next((item for item in rule.get("violations", []) if item.get("blocking")), None)
                if blocker:
                    reason = blocker.get("code", "RULE_REJECTED")
                    entry.status = "SKIPPED"
                    entry.skip_reason = reason
                    skipped += 1
                    if reason in {"TIME_CONFLICT", "CONFLICT"}:
                        conflicts += 1
                    results.append({"entity_type": "WAITLIST", "entity_id": entry.id, "student_id": entry.student_id, "old_status": "WAITING", "new_status": "SKIPPED", "reason_code": reason, "details": {"violations": rule.get("violations", []), "decision": rule.get("decision")}})
                    await _write_audit(
                        self.session,
                        actor_id=run_model.operator_id or "system",
                        actor_role="ACADEMIC",
                        action="WAITLIST_SKIPPED",
                        resource_type="waitlist_entry",
                        resource_id=entry.id,
                        request_id=f"run:{run_id}",
                        subject_student_id=entry.student_id,
                        before={**course_snapshot, "status": "WAITING"},
                        after={**course_snapshot, "status": "SKIPPED"},
                        reason=reason,
                        run_id=run_id,
                    )
                    continue
                if available <= 0:
                    results.append({"entity_type": "WAITLIST", "entity_id": entry.id, "student_id": entry.student_id, "old_status": "WAITING", "new_status": "WAITING", "reason_code": "CAPACITY_FULL", "details": {"capacity": course.capacity, "occupied": occupied}})
                    continue
                entry.status = "PROMOTED"
                await _upsert_enrollment(self.session, entry.student_id, course.id, source="PROMOTED")
                available -= 1
                occupied += 1
                promoted += 1
                results.append({"entity_type": "WAITLIST", "entity_id": entry.id, "student_id": entry.student_id, "old_status": "WAITING", "new_status": "PROMOTED", "reason_code": "ELIGIBLE", "details": {"position_at_start": entry.position}})
                await _write_audit(
                    self.session,
                    actor_id=run_model.operator_id or "system",
                    actor_role="ACADEMIC",
                    action="WAITLIST_PROMOTED",
                    resource_type="waitlist_entry",
                    resource_id=entry.id,
                    request_id=f"run:{run_id}",
                    subject_student_id=entry.student_id,
                    before={**course_snapshot, "status": "WAITING"},
                    after={**course_snapshot, "status": "PROMOTED"},
                    reason="ELIGIBLE",
                    run_id=run_id,
                )
            remaining = list((await self.session.execute(select(WaitlistEntry).where(WaitlistEntry.course_id == course.id, WaitlistEntry.status == "WAITING").order_by(WaitlistEntry.joined_at, WaitlistEntry.id).with_for_update())).scalars().all())
            for position, entry in enumerate(remaining, start=1):
                entry.position = position
            await self._finish_run(run_id, results=results, checked=len(waiting), promoted=promoted, skipped=skipped, conflicts=conflicts, waiting=len(remaining))
            return await self._run(run_id)
        except Exception as exc:
            run_model.status = "FAILED"
            run_model.error_json = _json_dump({"code": str(exc).split(":", 1)[0], "message": str(exc)})
            run_model.finished_at = _utcnow()
            await self.session.flush()
            raise

    async def _finish_run(self, run_id: str, *, results: list[dict], checked: int, promoted: int = 0, skipped: int = 0, conflicts: int = 0, waiting: int = 0) -> None:
        run = (await self.session.execute(select(RunModel).where(RunModel.id == run_id).with_for_update())).scalar_one()
        for item in results:
            self.session.add(
                ResultModel(
                    run_id=run_id,
                    entity_type=item["entity_type"],
                    entity_id=item["entity_id"],
                    student_id=item.get("student_id"),
                    old_status=item.get("old_status"),
                    new_status=item.get("new_status"),
                    reason_code=item["reason_code"],
                    details_json=_json_dump(item.get("details", {})),
                )
            )
        run.status = "SUCCEEDED"
        run.summary_json = _json_dump({"checked": checked, "promoted": promoted, "skipped": skipped, "conflicts": conflicts, "waiting": waiting, "errors": 0})
        run.finished_at = _utcnow()
        await self.session.flush()

    @staticmethod
    def _validate_schedules(schedules: list[dict]) -> None:
        if not schedules:
            raise _run_error("INVALID_SCHEDULE")
        normalized = []
        for item in schedules:
            weekday = int(item.get("weekday", 0))
            start = int(item.get("start_minute", -1))
            end = int(item.get("end_minute", -1))
            if not 1 <= weekday <= 7 or not 0 <= start < end <= 1440:
                raise _run_error("INVALID_SCHEDULE")
            normalized.append((weekday, start, end))
        for index, left in enumerate(normalized):
            for right in normalized[index + 1 :]:
                if left[0] == right[0] and left[1] < right[2] and right[1] < left[2]:
                    raise _run_error("INVALID_SCHEDULE")

    async def list_approvals(self, *, status: str | None = None, course_id: str | None = None, student_id: str | None = None) -> list[dict]:
        query = select(ExceptionApproval).order_by(ExceptionApproval.created_at.desc(), ExceptionApproval.id.desc())
        if status:
            query = query.where(ExceptionApproval.status == status)
        if course_id:
            query = query.where(ExceptionApproval.course_id == course_id)
        if student_id:
            query = query.where(ExceptionApproval.student_id == student_id)
        records = list((await self.session.execute(query)).scalars().all())
        return [self._approval_payload(item) for item in records]

    @staticmethod
    def _approval_payload(item: ExceptionApproval) -> dict:
        return {
            "id": item.id,
            "request_id": item.request_id,
            "enrollment_id": item.enrollment_id,
            "student_id": item.student_id,
            "course_id": item.course_id,
            "status": item.status,
            "rule_violations": _json_load(item.rule_violations, []),
            "waived_rules": _json_load(item.waived_rules, []),
            "reviewer_id": item.reviewer_id,
            "comment": item.comment,
            "created_at": item.created_at.isoformat() if item.created_at else None,
            "updated_at": item.updated_at.isoformat() if item.updated_at else None,
        }

    async def decide_approval(self, *, approval_id: str, decision: str, comment: str, waived_rules: list[str], reviewer_id: str, request_id: str) -> dict:
        if not comment.strip():
            raise _run_error("EMPTY_COMMENT")
        invalid = sorted(set(waived_rules) - ALLOWED_WAIVED_RULES)
        if invalid:
            raise _run_error("APPROVAL_RULE_NOT_ALLOWED")
        approval = (await self.session.execute(select(ExceptionApproval).where(ExceptionApproval.id == approval_id).with_for_update())).scalar_one_or_none()
        if approval is None:
            raise _run_error("APPROVAL_NOT_FOUND")
        if approval.status != "PENDING":
            raise _run_error("APPROVAL_NOT_PENDING")
        if decision == "REJECT":
            approval.status = "REJECTED"
        else:
            course = await _course(self.session, approval.course_id, lock=True)
            if course is None:
                raise _run_error("COURSE_NOT_FOUND")
            if course.status == "CANCELLED":
                raise _run_error("COURSE_CANCELLED")
            rule = await check_enrollment(self.session, approval.student_id, approval.course_id, waived_rules=set(waived_rules))
            if not rule["eligible"]:
                blockers = [item for item in rule["violations"] if item.get("blocking") and item.get("code") not in set(waived_rules)]
                if blockers:
                    raise _run_error("APPROVAL_RECHECK_FAILED")
            occupied = (await self.session.execute(select(func.count()).select_from(Enrollment).where(Enrollment.course_id == course.id, Enrollment.status.in_(ACTIVE_ENROLLMENT_STATUSES)))).scalar_one()
            if occupied >= course.capacity:
                raise _run_error("APPROVAL_RECHECK_FAILED")
            enrollment = await _upsert_enrollment(self.session, approval.student_id, approval.course_id, source="EXCEPTION")
            approval.enrollment_id = enrollment.id
            approval.status = "APPROVED"
        approval.reviewer_id = reviewer_id
        approval.comment = comment
        approval.waived_rules = _json_dump(waived_rules)
        approval.updated_at = _utcnow()
        await self.session.flush()
        await _write_audit(self.session, actor_id=reviewer_id, actor_role="ACADEMIC", action=f"APPROVAL_{approval.status}", resource_type="exception_approval", resource_id=approval.id, request_id=request_id, subject_student_id=approval.student_id, after=self._approval_payload(approval), reason=comment)
        return self._approval_payload(approval)

    async def list_audits(self, *, course_id: str | None = None, student_id: str | None = None, action: str | None = None, run_id: str | None = None, from_: datetime | None = None, to: datetime | None = None) -> tuple[list[dict], int]:
        query = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        if student_id:
            query = query.where(AuditLog.subject_student_id == student_id)
        if action:
            query = query.where(AuditLog.action == action)
        if run_id:
            query = query.where(AuditLog.run_id == run_id)
        if course_id:
            query = query.where(AuditLog.resource_id == course_id)
        if from_:
            query = query.where(AuditLog.created_at >= from_)
        if to:
            query = query.where(AuditLog.created_at <= to)
        records = list((await self.session.execute(query)).scalars().all())
        values = [
            {
                "id": item.id,
                "actor_id": item.actor_id or "system",
                "subject_student_id": item.subject_student_id,
                "actor_role": item.actor_role,
                "action": item.action,
                "resource_type": item.resource_type,
                "resource_id": item.resource_id,
                "before_json": _json_load(item.before_json, {}),
                "after_json": _json_load(item.after_json, {}),
                "reason": item.reason,
                "run_id": item.run_id,
                "request_id": item.request_id,
                "created_at": item.created_at.isoformat(),
            }
            for item in records
        ]
        return values, len(values)
