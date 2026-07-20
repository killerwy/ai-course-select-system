from __future__ import annotations

import copy
from typing import Any

from ..contracts import Role
from ..schemas.admin import ApprovalStatus
from ..utils import ALLOWED_WAIVED_RULES
from .audit import build_audit_record


class ApprovalService:
    def __init__(self, *, repository: Any, rule_checker: Any, audit_writer: Any | None = None) -> None:
        self.repository = repository
        self.rule_checker = rule_checker
        self.audit_writer = audit_writer

    async def approve(self, *, approval_id: str, comment: str, waived_rules: list[str], reviewer_id: str) -> dict[str, Any]:
        if not comment.strip():
            raise ValueError("EMPTY_COMMENT")
        snapshot = await self.repository.snapshot() if hasattr(self.repository, "snapshot") else None
        try:
            approval = await self.repository.lock_approval(approval_id)
            if approval.status != ApprovalStatus.PENDING:
                raise ValueError("APPROVAL_NOT_PENDING")
            invalid_rules = sorted(set(waived_rules) - ALLOWED_WAIVED_RULES)
            if invalid_rules:
                raise ValueError("APPROVAL_RULE_NOT_ALLOWED")
            course = await self.repository.get_course(approval.course_id)
            if course.get("status") == "CANCELLED":
                raise ValueError("COURSE_CANCELLED")
            rule_result = await self.rule_checker.check_enrollment(
                approval.student_id,
                approval.course_id,
                waived_rules=set(waived_rules),
            )
            remaining_blockers = [
                violation
                for violation in rule_result.get("violations", [])
                if violation.get("blocking") and violation.get("code") not in set(waived_rules)
            ]
            if remaining_blockers or not rule_result.get("eligible", False):
                raise ValueError("APPROVAL_RECHECK_FAILED")
            if await self.repository.occupied_count(approval.course_id) >= int(course.get("capacity", 0)):
                raise ValueError("APPROVAL_RECHECK_FAILED")
            before_enrollment = next(
                (item for item in await self.repository.list_enrollments(approval.course_id) if item.get("student_id") == approval.student_id),
                {"status": "NONE"},
            )
            enrollment = await self.repository.upsert_enrollment(approval.student_id, approval.course_id, "ENROLLED")
            updated = await self.repository.update_approval(
                approval_id,
                {
                    "status": ApprovalStatus.APPROVED.value,
                    "reviewer_id": reviewer_id,
                    "comment": comment,
                    "waived_rules": list(waived_rules),
                },
            )
            audit_id = await self._audit(
                reviewer_id,
                approval,
                before_enrollment,
                enrollment,
                comment,
                "EXCEPTION_APPROVED",
            )
            return {"approval": updated, "enrollment": enrollment, "audit_id": audit_id}
        except Exception:
            if snapshot is not None:
                await self.repository.restore(snapshot)
            raise

    async def reject(self, *, approval_id: str, comment: str, reviewer_id: str) -> dict[str, Any]:
        if not comment.strip():
            raise ValueError("EMPTY_COMMENT")
        approval = await self.repository.lock_approval(approval_id)
        if approval.status != ApprovalStatus.PENDING:
            raise ValueError("APPROVAL_NOT_PENDING")
        updated = await self.repository.update_approval(
            approval_id,
            {"status": ApprovalStatus.REJECTED.value, "reviewer_id": reviewer_id, "comment": comment},
        )
        audit_id = await self._audit(
            reviewer_id,
            approval,
            {"status": "PENDING"},
            {"status": "REJECTED"},
            comment,
            "EXCEPTION_REJECTED",
        )
        return {"approval": updated, "audit_id": audit_id}

    async def _audit(self, reviewer_id: str, approval: Any, before: Any, after: Any, reason: str, action: str) -> str | None:
        if self.audit_writer is None:
            return None
        record = build_audit_record(
            actor_id=reviewer_id,
            actor_role=Role.ACADEMIC,
            action=action,
            resource_type="exception_approval",
            resource_id=approval.id,
            subject_student_id=approval.student_id,
            before_json={**before, "course_id": approval.course_id},
            after_json={**after, "course_id": approval.course_id},
            reason=reason,
            request_id=f"approval:{approval.id}",
        )
        await self.audit_writer.append(record)
        return record.id
