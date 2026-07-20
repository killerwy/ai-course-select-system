from __future__ import annotations

import copy
from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4

from ..contracts import Role
from ..schemas.admin import ApprovalStatus, CourseOperationType
from .audit import build_audit_record


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _public_operation(value: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(value))
    result["payload"] = copy.deepcopy(result.get("payload") or {})
    return result


def decorate_courses_with_pending(courses: list[Mapping[str, Any]], operations: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Replace live course cards with pending previews without mutating storage."""
    values = [copy.deepcopy(dict(course)) for course in courses]
    by_id = {str(course.get("id")): course for course in values}
    pending = [item for item in operations if item.get("status") == ApprovalStatus.PENDING.value]
    for raw in pending:
        operation = _public_operation(raw)
        payload = operation.get("payload") or {}
        course_id = operation.get("course_id")
        if operation.get("operation") == CourseOperationType.CREATE.value:
            preview = {
                "id": f"pending-{operation['id']}",
                "code": payload.get("code", ""),
                "name": payload.get("name", ""),
                "teacher_name": payload.get("teacher_name", ""),
                "credits": payload.get("credits", 0),
                "capacity": payload.get("capacity", 0),
                "enrolled_count": 0,
                "waitlist_count": 0,
                "status": "PENDING_APPROVAL",
                "version": 0,
                "schedules": copy.deepcopy(payload.get("schedules") or []),
                "prerequisites": copy.deepcopy(payload.get("prerequisites") or []),
            }
            preview["pending_operation"] = operation
            values.append(preview)
            continue
        course = by_id.get(str(course_id))
        if course is None:
            continue
        if operation.get("operation") == CourseOperationType.UPDATE.value:
            for key in ("code", "name", "teacher_name", "credits", "capacity", "schedules", "prerequisites"):
                if key in payload:
                    course[key] = copy.deepcopy(payload[key])
        course["status"] = "PENDING_APPROVAL"
        course["pending_operation"] = operation
    return values


class CourseOperationApprovalService:
    def __init__(self, *, repository: Any, mutation_service: Any, audit_writer: Any | None = None) -> None:
        self.repository = repository
        self.mutation_service = mutation_service
        self.audit_writer = audit_writer

    async def submit(
        self,
        *,
        operation: str,
        course_id: str | None,
        payload: Mapping[str, Any],
        requester_id: str,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        if operation not in {item.value for item in CourseOperationType}:
            raise ValueError("INVALID_COURSE_OPERATION")
        if idempotency_key:
            existing = self.repository.course_operation_approvals.get(idempotency_key)
            if existing is not None:
                return {"operation": _public_operation(existing), "reused": True}
        if course_id and any(item.get("course_id") == course_id and item.get("status") == "PENDING" for item in self.repository.course_operation_approvals.values()):
            raise ValueError("COURSE_OPERATION_PENDING")
        code = str(payload.get("code", "")).strip()
        if operation == CourseOperationType.CREATE.value:
            self.mutation_service._validate_schedules(payload.get("schedules") or [])
            if not code or not str(payload.get("name", "")).strip() or not str(payload.get("teacher_name", "")).strip():
                raise ValueError("INVALID_COURSE")
            if any(str(item.get("code", "")) == code for item in self.repository.courses.values()):
                raise ValueError("COURSE_ALREADY_EXISTS")
            if any(
                item.get("operation") == CourseOperationType.CREATE.value
                and item.get("status") == "PENDING"
                and str((item.get("payload") or {}).get("code", "")) == code
                for item in self.repository.course_operation_approvals.values()
            ):
                raise ValueError("COURSE_OPERATION_PENDING")
        elif operation == CourseOperationType.UPDATE.value:
            course = await self.repository.lock_course(str(course_id), payload.get("expected_version"))
            self.mutation_service._validate_schedules(payload.get("schedules") or [])
            if any(str(item.get("code", "")) == code and str(item.get("id")) != course_id for item in self.repository.courses.values()):
                raise ValueError("COURSE_ALREADY_EXISTS")
            if course.get("status") == "CANCELLED":
                raise ValueError("COURSE_CANCELLED")
        elif operation == CourseOperationType.CANCEL.value:
            course = await self.repository.lock_course(str(course_id), payload.get("expected_version"))
            if not str(payload.get("reason", "")).strip():
                raise ValueError("EMPTY_REASON")
            payload = {**payload, "code": course.get("code"), "name": course.get("name")}
        operation_id = str(uuid4())
        record = {
            "id": operation_id,
            "operation": operation,
            "course_id": course_id,
            "requester_id": requester_id,
            "reviewer_id": None,
            "status": "PENDING",
            "payload": copy.deepcopy(dict(payload)),
            "reason": payload.get("reason"),
            "comment": None,
            "idempotency_key": idempotency_key,
            "created_at": _now(),
            "updated_at": _now(),
        }
        self.repository.course_operation_approvals[operation_id] = record
        if idempotency_key:
            self.repository.course_operation_approvals[idempotency_key] = record
        await self._audit(requester_id, "COURSE_OPERATION_SUBMITTED", record, "course operation submitted")
        return {"operation": _public_operation(record), "reused": False}

    async def list(self, *, status: str | None = None, course_id: str | None = None) -> list[dict[str, Any]]:
        values = []
        seen: set[str] = set()
        for record in self.repository.course_operation_approvals.values():
            if record["id"] in seen:
                continue
            seen.add(record["id"])
            if status and record.get("status") != status:
                continue
            if course_id and record.get("course_id") != course_id:
                continue
            values.append(_public_operation(record))
        return sorted(values, key=lambda item: (str(item.get("created_at", "")), str(item.get("id", ""))), reverse=True)

    async def decide(self, *, operation_id: str, decision: str, comment: str, reviewer_id: str) -> dict[str, Any]:
        if not comment.strip():
            raise ValueError("EMPTY_COMMENT")
        record = self.repository.course_operation_approvals.get(operation_id)
        if record is None:
            raise ValueError("COURSE_OPERATION_NOT_FOUND")
        if record.get("status") != "PENDING":
            raise ValueError("COURSE_OPERATION_NOT_PENDING")
        if decision == "REJECT":
            record.update({"status": "REJECTED", "reviewer_id": reviewer_id, "comment": comment, "updated_at": _now()})
            await self._audit(reviewer_id, "COURSE_OPERATION_REJECTED", record, comment)
            return {"operation": _public_operation(record), "course": copy.deepcopy(self.repository.courses.get(record.get("course_id"))), "run": None, "reused": False}
        payload = record.get("payload") or {}
        operation = record.get("operation")
        if operation == CourseOperationType.CREATE.value:
            result = await self.mutation_service.create(operator_id=reviewer_id, **payload)
            record["course_id"] = result["course"]["id"]
        elif operation == CourseOperationType.UPDATE.value:
            result = await self.mutation_service.update_details(course_id=record["course_id"], operator_id=reviewer_id, **payload)
        elif operation == CourseOperationType.CANCEL.value:
            result = await self.mutation_service.cancel(course_id=record["course_id"], operator_id=reviewer_id, idempotency_key=f"operation-cancel-{record['id']}", reason=payload.get("reason", ""), expected_version=payload.get("expected_version"))
            await self.repository.delete_course(record["course_id"])
            result["course"] = None
        else:
            raise ValueError("INVALID_COURSE_OPERATION")
        record.update({"status": "APPROVED", "reviewer_id": reviewer_id, "comment": comment, "updated_at": _now()})
        await self._audit(reviewer_id, "COURSE_OPERATION_APPROVED", record, comment)
        return {"operation": _public_operation(record), "course": copy.deepcopy(result.get("course")), "run": result.get("run"), "reused": result.get("reused", False)}

    async def _audit(self, actor_id: str, operation: str, record: Mapping[str, Any], reason: str) -> None:
        if self.audit_writer is None:
            return
        await self.audit_writer.append(
            build_audit_record(
                actor_id=actor_id,
                actor_role=Role.ACADEMIC,
                action=operation,
                resource_type="course_operation",
                resource_id=str(record["id"]),
                before_json={},
                after_json=_public_operation(record),
                reason=reason,
                request_id=f"course-operation:{record['id']}",
                created_at=datetime.now(timezone.utc),
            )
        )
