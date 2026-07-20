from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any

from ..schemas.admin import ApprovalRecord


class InMemoryAdminRepository:
    """Deterministic adapter for C service tests before A's database repository."""

    def __init__(
        self,
        *,
        courses: list[Mapping[str, Any]] | None = None,
        enrollments: list[Mapping[str, Any]] | None = None,
        waitlists: list[Mapping[str, Any]] | None = None,
        approvals: list[Mapping[str, Any]] | None = None,
    ) -> None:
        self.courses = {str(course["id"]): copy.deepcopy(dict(course)) for course in courses or []}
        self.enrollments: dict[tuple[str, str], dict[str, Any]] = {}
        for enrollment in enrollments or []:
            value = copy.deepcopy(dict(enrollment))
            self.enrollments[(str(value["student_id"]), str(value["course_id"]))] = value
        self.waitlists: dict[str, dict[str, Any]] = {}
        for index, waitlist in enumerate(waitlists or [], start=1):
            value = copy.deepcopy(dict(waitlist))
            value.setdefault("id", f"wait-{index:03d}")
            self.waitlists[str(value["id"])] = value
        self.approvals: dict[str, dict[str, Any]] = {
            str(value["id"]): copy.deepcopy(dict(value)) for value in approvals or []
        }

    async def lock_course(self, course_id: str, expected_version: int | None = None) -> dict[str, Any]:
        course = self.courses.get(course_id)
        if course is None:
            raise KeyError(course_id)
        actual_version = course.get("version")
        if expected_version is not None and actual_version != expected_version:
            raise ValueError("CONCURRENT_MODIFICATION")
        return course

    async def update_course(self, course: Mapping[str, Any]) -> None:
        self.courses[str(course["id"])] = copy.deepcopy(dict(course))

    async def list_enrollments(self, course_id: str) -> list[dict[str, Any]]:
        return [copy.deepcopy(value) for value in self.enrollments.values() if value["course_id"] == course_id]

    async def list_course_waitlists(self, course_id: str) -> list[dict[str, Any]]:
        return [copy.deepcopy(value) for value in self.waitlists.values() if value["course_id"] == course_id]

    async def update_enrollment_status(self, student_id: str, course_id: str, status: str) -> dict[str, Any]:
        enrollment = self.enrollments[(student_id, course_id)]
        enrollment["status"] = status
        return copy.deepcopy(enrollment)

    async def update_waitlist_status(self, entry_id: str, status: str) -> dict[str, Any]:
        entry = self.waitlists[entry_id]
        entry["status"] = status
        return copy.deepcopy(entry)

    async def get_course(self, course_id: str) -> dict[str, Any]:
        return await self.lock_course(course_id)

    async def occupied_count(self, course_id: str) -> int:
        return sum(
            1
            for item in self.enrollments.values()
            if item["course_id"] == course_id and item.get("status") in {"ENROLLED", "CONFLICT_REVIEW"}
        )

    async def upsert_enrollment(self, student_id: str, course_id: str, status: str) -> dict[str, Any]:
        enrollment = self.enrollments.setdefault(
            (student_id, course_id),
            {"student_id": student_id, "course_id": course_id, "source": "EXCEPTION_APPROVAL"},
        )
        enrollment["status"] = status
        return copy.deepcopy(enrollment)

    async def lock_approval(self, approval_id: str) -> ApprovalRecord:
        value = self.approvals.get(approval_id)
        if value is None:
            raise KeyError(approval_id)
        return ApprovalRecord.model_validate(value)

    async def update_approval(self, approval_id: str, patch: Mapping[str, Any]) -> ApprovalRecord:
        value = self.approvals[approval_id]
        value.update(copy.deepcopy(dict(patch)))
        record = ApprovalRecord.model_validate(value)
        self.approvals[approval_id] = record.model_dump(mode="json")
        return record

    async def list_approvals(self, filters: Mapping[str, Any] | None = None) -> list[ApprovalRecord]:
        filters = filters or {}
        values = list(self.approvals.values())
        for key in ("status", "course_id", "student_id"):
            expected = filters.get(key)
            if expected:
                values = [value for value in values if value.get(key) == expected]
        return [ApprovalRecord.model_validate(value) for value in values]

    async def list_waiting(self, course_id: str) -> list[dict[str, Any]]:
        return [
            copy.deepcopy(value)
            for value in self.waitlists.values()
            if value["course_id"] == course_id and value.get("status") == "WAITING"
        ]

    async def promote_waitlist(self, entry_id: str, student_id: str, course_id: str) -> dict[str, Any]:
        entry = self.waitlists[entry_id]
        entry["status"] = "PROMOTED"
        enrollment = {
            "student_id": student_id,
            "course_id": course_id,
            "status": "ENROLLED",
            "source": "WAITLIST",
        }
        self.enrollments[(student_id, course_id)] = enrollment
        return copy.deepcopy(enrollment)

    async def skip_waitlist(self, entry_id: str, reason_code: str, details: Mapping[str, Any]) -> dict[str, Any]:
        entry = self.waitlists[entry_id]
        entry["status"] = "SKIPPED"
        entry["skip_reason"] = reason_code
        entry["skip_details"] = copy.deepcopy(dict(details))
        return copy.deepcopy(entry)

    async def renumber_waitlist(self, course_id: str) -> None:
        waiting = sorted(
            (value for value in self.waitlists.values() if value["course_id"] == course_id and value.get("status") == "WAITING"),
            key=lambda value: (str(value.get("joined_at", "")), str(value.get("id", ""))),
        )
        for position, entry in enumerate(waiting, start=1):
            entry["position"] = position

    async def snapshot(self) -> dict[str, Any]:
        return {"courses": copy.deepcopy(self.courses), "enrollments": copy.deepcopy(self.enrollments), "waitlists": copy.deepcopy(self.waitlists), "approvals": copy.deepcopy(self.approvals)}

    async def restore(self, snapshot: Mapping[str, Any]) -> None:
        self.courses = copy.deepcopy(snapshot["courses"])
        self.enrollments = copy.deepcopy(snapshot["enrollments"])
        self.waitlists = copy.deepcopy(snapshot["waitlists"])
        self.approvals = copy.deepcopy(snapshot["approvals"])


class InMemoryAuditWriter:
    def __init__(self) -> None:
        self.records: list[Any] = []

    async def append(self, record: Any) -> Any:
        self.records.append(record)
        return record
