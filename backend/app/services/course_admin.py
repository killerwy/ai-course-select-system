from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from ..contracts import CourseSchedule, Role
from ..schemas.admin import RecalculationResult, RecalculationSummary, RunStatus, TriggerType
from .audit import build_audit_record
from .runs import RunRegistry


class CourseMutationService:
    """Validate and persist course mutations before the shared recalculation run."""

    def __init__(self, *, repository: Any, run_registry: RunRegistry, audit_writer: Any | None = None) -> None:
        self.repository = repository
        self.run_registry = run_registry
        self.audit_writer = audit_writer

    async def create(
        self,
        *,
        code: str,
        name: str,
        teacher_name: str,
        credits: int,
        capacity: int,
        schedules: list[CourseSchedule | Mapping[str, Any]],
        prerequisites: list[str] | None = None,
        operator_id: str,
    ) -> dict[str, Any]:
        if not code.strip() or not name.strip() or not teacher_name.strip() or credits <= 0 or capacity <= 0:
            raise ValueError("INVALID_COURSE")
        normalized = self._validate_schedules(schedules)
        course = {
            "id": str(uuid4()),
            "code": code.strip(),
            "name": name.strip(),
            "teacher_name": teacher_name.strip(),
            "credits": int(credits),
            "capacity": int(capacity),
            "status": "OPEN",
            "version": 1,
            "schedules": normalized,
            "prerequisites": list(prerequisites or []),
        }
        await self.repository.create_course(course)
        if self.audit_writer is not None:
            await self.audit_writer.append(
                build_audit_record(
                    actor_id=operator_id,
                    actor_role=Role.ACADEMIC,
                    action="COURSE_CREATED",
                    resource_type="course",
                    resource_id=course["id"],
                    before_json={},
                    after_json=course,
                    reason="course created",
                    request_id=f"course:{course['id']}",
                    created_at=datetime.now(timezone.utc),
                )
            )
        return {"course": copy.deepcopy(course), "run": None, "reused": False}

    async def update_details(
        self,
        *,
        course_id: str,
        code: str,
        name: str,
        teacher_name: str,
        credits: int,
        capacity: int,
        schedules: list[CourseSchedule | Mapping[str, Any]],
        prerequisites: list[str] | None = None,
        operator_id: str,
        idempotency_key: str | None = None,
        expected_version: int | None = None,
    ) -> dict[str, Any]:
        if not code.strip() or not name.strip() or not teacher_name.strip() or credits <= 0 or capacity <= 0:
            raise ValueError("INVALID_COURSE")
        normalized = self._validate_schedules(schedules)
        course = await self.repository.lock_course(course_id, expected_version)
        if course.get("status") == "CANCELLED":
            raise ValueError("COURSE_CANCELLED")
        if any(str(item.get("code", "")) == code.strip() and str(item.get("id")) != course_id for item in self.repository.courses.values()):
            raise ValueError("COURSE_ALREADY_EXISTS")
        before = copy.deepcopy(course)
        updated = {
            **course,
            "code": code.strip(),
            "name": name.strip(),
            "teacher_name": teacher_name.strip(),
            "credits": int(credits),
            "capacity": int(capacity),
            "schedules": normalized,
            "prerequisites": list(prerequisites or []),
            "version": int(course.get("version", 0)) + 1,
        }
        run, reused = await self.run_registry.start(
            course_id=course_id,
            trigger_type=TriggerType.COURSE_UPDATE,
            operator_id=operator_id,
            idempotency_key=idempotency_key,
        )
        if reused:
            return {"course": copy.deepcopy(course), "run": run, "reused": True}
        await self.repository.update_course(updated)
        await self._audit_course(operator_id, course_id, before, updated, "course details updated", run.id, "COURSE_UPDATED")
        return {"course": copy.deepcopy(updated), "run": run, "reused": False}

    async def expand(
        self,
        *,
        course_id: str,
        capacity_delta: int,
        operator_id: str,
        idempotency_key: str | None = None,
        expected_version: int | None = None,
    ) -> dict[str, Any]:
        if capacity_delta <= 0:
            raise ValueError("INVALID_CAPACITY_DELTA")
        return await self._mutate_course(
            course_id=course_id,
            trigger_type=TriggerType.EXPAND,
            operator_id=operator_id,
            idempotency_key=idempotency_key,
            expected_version=expected_version,
            mutate=lambda course: {**course, "capacity": int(course.get("capacity", 0)) + capacity_delta},
            audit_action="COURSE_EXPANDED",
            reason=f"capacity +{capacity_delta}",
        )

    async def reschedule(
        self,
        *,
        course_id: str,
        schedules: list[CourseSchedule | Mapping[str, Any]],
        operator_id: str,
        idempotency_key: str | None = None,
        expected_version: int | None = None,
    ) -> dict[str, Any]:
        normalized = self._validate_schedules(schedules)
        return await self._mutate_course(
            course_id=course_id,
            trigger_type=TriggerType.RESCHEDULE,
            operator_id=operator_id,
            idempotency_key=idempotency_key,
            expected_version=expected_version,
            mutate=lambda course: {**course, "schedules": normalized},
            audit_action="COURSE_RESCHEDULED",
            reason="course schedules changed",
        )

    async def cancel(
        self,
        *,
        course_id: str,
        reason: str,
        operator_id: str,
        idempotency_key: str | None = None,
        expected_version: int | None = None,
    ) -> dict[str, Any]:
        if not reason.strip():
            raise ValueError("EMPTY_REASON")
        snapshot = await self.repository.snapshot() if hasattr(self.repository, "snapshot") else None
        run, reused = await self.run_registry.start(
            course_id=course_id,
            trigger_type=TriggerType.CANCEL,
            operator_id=operator_id,
            idempotency_key=idempotency_key,
        )
        if reused:
            return {"course": copy.deepcopy(self.repository.courses[course_id]), "run": run, "reused": True}
        try:
            course = await self.repository.lock_course(course_id, expected_version)
            if course.get("status") == "CANCELLED":
                raise ValueError("COURSE_ALREADY_CANCELLED")
            before = copy.deepcopy(course)
            course = {**course, "status": "CANCELLED", "version": int(course.get("version", 0)) + 1}
            await self.repository.update_course(course)
            results: list[RecalculationResult] = []
            for enrollment in await self.repository.list_enrollments(course_id):
                student_id = str(enrollment["student_id"])
                await self.repository.update_enrollment_status(student_id, course_id, "CANCELLED_BY_ADMIN")
                entity_id = str(enrollment.get("id") or f"{student_id}:{course_id}")
                results.append(RecalculationResult(entity_type="ENROLLMENT", entity_id=entity_id, student_id=student_id, old_status=str(enrollment.get("status")), new_status="CANCELLED_BY_ADMIN", reason_code="COURSE_CANCELLED"))
                await self._audit_student_course_deleted(
                    operator_id=operator_id,
                    course=course,
                    student_id=student_id,
                    resource_type="enrollment",
                    resource_id=entity_id,
                    old_status=str(enrollment.get("status")),
                    new_status="CANCELLED_BY_ADMIN",
                    run_id=run.id,
                )
            for entry in await self.repository.list_course_waitlists(course_id):
                await self.repository.update_waitlist_status(str(entry["id"]), "CLOSED")
                results.append(RecalculationResult(entity_type="WAITLIST", entity_id=str(entry["id"]), student_id=str(entry["student_id"]), old_status=str(entry.get("status")), new_status="CLOSED", reason_code="COURSE_CANCELLED"))
                await self._audit_student_course_deleted(
                    operator_id=operator_id,
                    course=course,
                    student_id=str(entry["student_id"]),
                    resource_type="waitlist_entry",
                    resource_id=str(entry["id"]),
                    old_status=str(entry.get("status")),
                    new_status="CLOSED",
                    run_id=run.id,
                )
            await self.run_registry.transition(run.id, RunStatus.RUNNING)
            done = await self.run_registry.transition(
                run.id,
                RunStatus.SUCCEEDED,
                summary=RecalculationSummary(checked=len(results)),
                results=results,
            )
            await self._audit_course(operator_id, course_id, before, course, reason, run.id, "COURSE_CANCELLED")
            return {"course": copy.deepcopy(course), "run": done, "reused": False}
        except Exception as exc:
            if snapshot is not None:
                await self.repository.restore(snapshot)
            await self.run_registry.fail(run.id, str(exc))
            raise

    async def _mutate_course(
        self,
        *,
        course_id: str,
        trigger_type: TriggerType,
        operator_id: str,
        idempotency_key: str | None,
        expected_version: int | None,
        mutate,
        audit_action: str,
        reason: str,
    ) -> dict[str, Any]:
        snapshot = await self.repository.snapshot() if hasattr(self.repository, "snapshot") else None
        run, reused = await self.run_registry.start(
            course_id=course_id,
            trigger_type=trigger_type,
            operator_id=operator_id,
            idempotency_key=idempotency_key,
        )
        if reused:
            return {"course": copy.deepcopy(self.repository.courses[course_id]), "run": run, "reused": True}
        try:
            course = await self.repository.lock_course(course_id, expected_version)
            if course.get("status") == "CANCELLED":
                raise ValueError("COURSE_CANCELLED")
            before = copy.deepcopy(course)
            updated = mutate(copy.deepcopy(course))
            updated["version"] = int(course.get("version", 0)) + 1
            await self.repository.update_course(updated)
            await self._audit_course(operator_id, course_id, before, updated, reason, run.id, audit_action)
            return {"course": copy.deepcopy(updated), "run": run, "reused": False}
        except Exception as exc:
            if snapshot is not None:
                await self.repository.restore(snapshot)
            await self.run_registry.fail(run.id, str(exc))
            raise

    @staticmethod
    def _validate_schedules(schedules: list[CourseSchedule | Mapping[str, Any]]) -> list[dict[str, Any]]:
        if not schedules:
            raise ValueError("INVALID_SCHEDULE")
        normalized = [item.model_dump() if isinstance(item, CourseSchedule) else dict(item) for item in schedules]
        for item in normalized:
            weekday = int(item.get("weekday", 0))
            start = int(item.get("start_minute", -1))
            end = int(item.get("end_minute", -1))
            if not 1 <= weekday <= 7 or not 0 <= start < end <= 1440:
                raise ValueError("INVALID_SCHEDULE")
        for index, left in enumerate(normalized):
            for right in normalized[index + 1 :]:
                if left["weekday"] != right["weekday"]:
                    continue
                if left["start_minute"] < right["end_minute"] and right["start_minute"] < left["end_minute"]:
                    raise ValueError("INVALID_SCHEDULE")
        return normalized

    async def _audit_course(self, operator_id: str, course_id: str, before: Mapping[str, Any], after: Mapping[str, Any], reason: str, run_id: str, action: str) -> None:
        if self.audit_writer is None:
            return
        await self.audit_writer.append(
            build_audit_record(
                actor_id=operator_id,
                actor_role=Role.ACADEMIC,
                action=action,
                resource_type="course",
                resource_id=course_id,
                before_json=before,
                after_json=after,
                reason=reason,
                run_id=run_id,
                request_id=f"run:{run_id}",
                created_at=datetime.now(timezone.utc),
            )
        )

    async def _audit_student_course_deleted(
        self,
        *,
        operator_id: str,
        course: Mapping[str, Any],
        student_id: str,
        resource_type: str,
        resource_id: str,
        old_status: str,
        new_status: str,
        run_id: str,
    ) -> None:
        if self.audit_writer is None:
            return
        course_snapshot = {
            "course_id": str(course["id"]),
            "course_code": str(course.get("code") or ""),
            "course_name": str(course.get("name") or course.get("code") or course["id"]),
        }
        await self.audit_writer.append(
            build_audit_record(
                actor_id=operator_id,
                actor_role=Role.ACADEMIC,
                subject_student_id=student_id,
                action="COURSE_DELETED_BY_TEACHER",
                resource_type=resource_type,
                resource_id=resource_id,
                before_json={**course_snapshot, "status": old_status},
                after_json={**course_snapshot, "status": new_status},
                reason=f"教师已删除课程《{course_snapshot['course_name']}》",
                run_id=run_id,
                request_id=f"run:{run_id}:student:{student_id}",
                created_at=datetime.now(timezone.utc),
            )
        )
