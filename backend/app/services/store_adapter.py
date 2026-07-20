"""Adapters that let the C admin services run against the baseline STORE.

The adapter deliberately owns no SQL or migration concerns.  It is a narrow
compatibility seam: group A can replace it with the SQLAlchemy repository
without changing the router/service contracts.
"""

from __future__ import annotations

import copy
import asyncio
from datetime import datetime, timezone
from typing import Any, Mapping

from ..contracts import Role
from ..schemas.admin import ApprovalRecord, AuditRecord
from ..store import STORE
from ..utils import schedules_overlap


def _waitlist_id(value: Mapping[str, Any], key: tuple[str, str] | None = None) -> str:
    if value.get("id"):
        return str(value["id"])
    if key:
        return f"wait:{key[0]}:{key[1]}"
    return f"wait:{value.get('student_id')}:{value.get('course_id')}"


class StoreAdminRepository:
    """Async-shaped repository over the existing process-local store."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    @property
    def courses(self) -> dict[str, dict[str, Any]]:
        return STORE.courses

    @property
    def enrollments(self) -> dict[tuple[str, str], dict[str, Any]]:
        return STORE.enrollments

    @property
    def course_operation_approvals(self) -> dict[str, dict[str, Any]]:
        return STORE.course_operation_approvals

    async def lock_course(self, course_id: str, expected_version: int | None = None) -> dict[str, Any]:
        async with self._lock:
            course = STORE.courses.get(course_id)
            if course is None:
                raise KeyError(course_id)
            actual_version = course.get("version", 0)
            if expected_version is not None and actual_version != expected_version:
                raise ValueError("CONCURRENT_MODIFICATION")
            return course

    async def update_course(self, course: Mapping[str, Any]) -> None:
        async with self._lock:
            STORE.courses[str(course["id"])] = copy.deepcopy(dict(course))

    async def delete_course(self, course_id: str) -> None:
        async with self._lock:
            STORE.courses.pop(course_id, None)
            for key in list(STORE.enrollments):
                if key[1] == course_id:
                    STORE.enrollments.pop(key, None)
            for key in list(STORE.waitlists):
                if key[1] == course_id:
                    STORE.waitlists.pop(key, None)

    async def create_course(self, course: Mapping[str, Any]) -> None:
        async with self._lock:
            code = str(course.get("code", ""))
            if any(str(item.get("code", "")) == code for item in STORE.courses.values()):
                raise ValueError("COURSE_ALREADY_EXISTS")
            STORE.courses[str(course["id"])] = copy.deepcopy(dict(course))

    async def list_enrollments(self, course_id: str) -> list[dict[str, Any]]:
        return [copy.deepcopy(item) for item in STORE.enrollments.values() if item.get("course_id") == course_id]

    def _list_waitlists(self, course_id: str, *, status: str | None = None) -> list[dict[str, Any]]:
        values: list[dict[str, Any]] = []
        for key, raw in STORE.waitlists.items():
            if raw.get("course_id") != course_id:
                continue
            item = copy.deepcopy(raw)
            item["id"] = _waitlist_id(item, key if isinstance(key, tuple) else None)
            if status is None or item.get("status") == status:
                values.append(item)
        return values

    async def list_course_waitlists(self, course_id: str) -> list[dict[str, Any]]:
        return self._list_waitlists(course_id)

    async def list_waiting(self, course_id: str) -> list[dict[str, Any]]:
        return self._list_waitlists(course_id, status="WAITING")

    def _find_waitlist(self, entry_id: str) -> tuple[tuple[str, str], dict[str, Any]]:
        for key, value in STORE.waitlists.items():
            candidate = _waitlist_id(value, key if isinstance(key, tuple) else None)
            if candidate == entry_id or str(value.get("id", "")) == entry_id:
                return key, value
        raise KeyError(entry_id)

    async def update_waitlist_status(self, entry_id: str, status: str) -> dict[str, Any]:
        async with self._lock:
            _, value = self._find_waitlist(entry_id)
            value["status"] = status
            return copy.deepcopy(value)

    async def promote_waitlist(self, entry_id: str, student_id: str, course_id: str) -> dict[str, Any]:
        async with self._lock:
            _, value = self._find_waitlist(entry_id)
            value["status"] = "PROMOTED"
            enrollment = {
                "student_id": student_id,
                "course_id": course_id,
                "status": "ENROLLED",
                "source": "WAITLIST",
            }
            STORE.enrollments[(student_id, course_id)] = enrollment
            return copy.deepcopy(enrollment)

    async def skip_waitlist(self, entry_id: str, reason_code: str, details: Mapping[str, Any]) -> dict[str, Any]:
        async with self._lock:
            _, value = self._find_waitlist(entry_id)
            value["status"] = "SKIPPED"
            value["skip_reason"] = reason_code
            value["skip_details"] = copy.deepcopy(dict(details))
            return copy.deepcopy(value)

    async def renumber_waitlist(self, course_id: str) -> None:
        async with self._lock:
            waiting = sorted(self._list_waitlists(course_id, status="WAITING"), key=lambda item: (str(item.get("joined_at", "")), str(item["id"])))
            for position, entry in enumerate(waiting, start=1):
                _, value = self._find_waitlist(entry["id"])
                value["position"] = position

    async def update_enrollment_status(self, student_id: str, course_id: str, status: str) -> dict[str, Any]:
        async with self._lock:
            enrollment = STORE.enrollments.get((student_id, course_id))
            if enrollment is None:
                raise KeyError((student_id, course_id))
            enrollment["status"] = status
            return copy.deepcopy(enrollment)

    async def get_course(self, course_id: str) -> dict[str, Any]:
        return await self.lock_course(course_id)

    async def occupied_count(self, course_id: str) -> int:
        return sum(1 for item in STORE.enrollments.values() if item.get("course_id") == course_id and item.get("status") in {"ENROLLED", "CONFLICT_REVIEW"})

    async def upsert_enrollment(self, student_id: str, course_id: str, status: str) -> dict[str, Any]:
        async with self._lock:
            enrollment = STORE.enrollments.setdefault(
                (student_id, course_id),
                {"student_id": student_id, "course_id": course_id, "source": "EXCEPTION_APPROVAL"},
            )
            enrollment["status"] = status
            return copy.deepcopy(enrollment)

    async def lock_approval(self, approval_id: str) -> ApprovalRecord:
        value = STORE.approvals.get(approval_id)
        if value is None:
            raise KeyError(approval_id)
        return ApprovalRecord.model_validate(value)

    async def update_approval(self, approval_id: str, patch: Mapping[str, Any]) -> ApprovalRecord:
        async with self._lock:
            value = STORE.approvals.get(approval_id)
            if value is None:
                raise KeyError(approval_id)
            value.update(copy.deepcopy(dict(patch)))
            record = ApprovalRecord.model_validate(value)
            STORE.approvals[approval_id] = record.model_dump(mode="json")
            return record

    async def list_approvals(self, filters: Mapping[str, Any] | None = None) -> list[ApprovalRecord]:
        values = list(STORE.approvals.values())
        filters = filters or {}
        for key in ("status", "course_id", "student_id"):
            expected = filters.get(key)
            if expected:
                values = [item for item in values if item.get(key) == expected]
        return [ApprovalRecord.model_validate(item) for item in values]

    async def snapshot(self) -> dict[str, Any]:
        async with self._lock:
            return {
                "courses": copy.deepcopy(STORE.courses),
                "enrollments": copy.deepcopy(STORE.enrollments),
                "waitlists": copy.deepcopy(STORE.waitlists),
                "approvals": copy.deepcopy(STORE.approvals),
                "course_operation_approvals": copy.deepcopy(STORE.course_operation_approvals),
            }

    async def restore(self, snapshot: Mapping[str, Any]) -> None:
        async with self._lock:
            STORE.courses = copy.deepcopy(snapshot["courses"])
            STORE.enrollments = copy.deepcopy(snapshot["enrollments"])
            STORE.waitlists = copy.deepcopy(snapshot["waitlists"])
            STORE.approvals = copy.deepcopy(snapshot["approvals"])
            STORE.course_operation_approvals = copy.deepcopy(snapshot.get("course_operation_approvals", {}))


class StoreAuditWriter:
    """Persist validated audit records in the baseline audit collection."""

    async def append(self, record: AuditRecord) -> AuditRecord:
        STORE.audits.append(record.model_dump(mode="json"))
        return record


class BaselineRuleChecker:
    """Deterministic compatibility checker until the shared rule engine is wired.

    This is intentionally conservative and replaceable.  It only evaluates
    prerequisite, duplicate, and schedule conflicts from baseline STORE data;
    authoritative rule decisions remain an A/B integration boundary.
    """

    def __init__(self, repository: StoreAdminRepository) -> None:
        self.repository = repository

    async def check_enrollment(self, student_id: str, course_id: str, *, waived_rules: set[str] | None = None) -> dict[str, Any]:
        waived = waived_rules or set()
        course = await self.repository.get_course(course_id)
        violations: list[dict[str, Any]] = []
        completed = {
            str(item.get("course_id"))
            for item in STORE.enrollments.values()
            if item.get("student_id") == student_id and item.get("status") == "ENROLLED"
        }
        missing = [item for item in course.get("prerequisites", []) if item not in completed]
        if missing and "PREREQUISITE_MISSING" not in waived:
            violations.append({"code": "PREREQUISITE_MISSING", "blocking": True, "details": {"course_ids": missing}})
        existing = [
            item for item in STORE.enrollments.values()
            if item.get("student_id") == student_id and item.get("course_id") == course_id and item.get("status") == "ENROLLED"
        ]
        if existing and "DUPLICATE" not in waived:
            violations.append({"code": "DUPLICATE", "blocking": True})
        schedules = course.get("schedules", [])
        for item in STORE.enrollments.values():
            if item.get("student_id") != student_id or item.get("status") != "ENROLLED" or item.get("course_id") == course_id:
                continue
            other = STORE.courses.get(str(item.get("course_id")), {})
            if schedules_overlap(schedules, other.get("schedules", [])) and "TIME_CONFLICT" not in waived:
                violations.append({"code": "TIME_CONFLICT", "blocking": True})
                break
        eligible = not any(item.get("blocking") for item in violations)
        return {
            "eligible": eligible,
            "decision": "ELIGIBLE" if eligible else str(violations[0].get("code", "RULE_REJECTED")),
            "violations": violations,
            "warnings": [],
            "checked_at": datetime.now(timezone.utc).isoformat(),
        }
