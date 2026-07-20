"""Tests for ApprovalService."""

import pytest

from app.schemas.admin import ApprovalStatus
from app.services.approval import ApprovalService
from app.services.in_memory import InMemoryAdminRepository, InMemoryAuditWriter


class ApprovalRuleChecker:
    def __init__(self, result):
        self.result = result
        self.calls = []

    async def check_enrollment(self, student_id, course_id, *, waived_rules=None):
        self.calls.append((student_id, course_id, waived_rules))
        return self.result


def build_approval_service(*, rule_result, status="PENDING", course_status="OPEN", capacity=2, enrollment_status="CONFLICT_REVIEW"):
    repository = InMemoryAdminRepository(
        courses=[{"id": "course-201", "capacity": capacity, "status": course_status}],
        enrollments=[{"student_id": "student-001", "course_id": "course-201", "status": enrollment_status}],
        approvals=[{"id": "approval-001", "student_id": "student-001", "course_id": "course-201", "status": status, "rule_violations": ["CONFLICT"]}],
    )
    audit_writer = InMemoryAuditWriter()
    service = ApprovalService(repository=repository, rule_checker=ApprovalRuleChecker(rule_result), audit_writer=audit_writer)
    return repository, audit_writer, service


@pytest.mark.asyncio
async def test_approve_allowed_rule_updates_enrollment_and_audit():
    """Approving with allowed rule updates enrollment and creates audit."""
    repository, audit_writer, service = build_approval_service(
        rule_result={"eligible": True, "decision": "ELIGIBLE", "violations": [], "warnings": [], "checked_at": "now"}
    )
    result = await service.approve(approval_id="approval-001", comment="确认豁免时间冲突", waived_rules=["CONFLICT"], reviewer_id="academic-001")
    assert result["approval"].status == ApprovalStatus.APPROVED
    assert repository.enrollments[("student-001", "course-201")]["status"] == "ENROLLED"
    assert len(audit_writer.records) == 1


@pytest.mark.asyncio
async def test_reject_keeps_enrollment_and_marks_approval_rejected():
    """Rejecting keeps enrollment status and marks approval as rejected."""
    repository, audit_writer, service = build_approval_service(
        rule_result={"eligible": False, "decision": "CONFLICT", "violations": [{"code": "CONFLICT", "blocking": True}], "warnings": [], "checked_at": "now"}
    )
    result = await service.reject(approval_id="approval-001", comment="不批准", reviewer_id="academic-001")
    assert result["approval"].status == ApprovalStatus.REJECTED
    assert repository.enrollments[("student-001", "course-201")]["status"] == "CONFLICT_REVIEW"
    assert len(audit_writer.records) == 1


@pytest.mark.asyncio
async def test_forbidden_rule_and_recheck_failure_keep_pending():
    """Forbidden rule and recheck failure keep approval pending."""
    repository, _, service = build_approval_service(
        rule_result={"eligible": False, "decision": "DUPLICATE", "violations": [{"code": "DUPLICATE", "blocking": True}], "warnings": [], "checked_at": "now"}
    )
    with pytest.raises(ValueError, match="APPROVAL_RULE_NOT_ALLOWED"):
        await service.approve(approval_id="approval-001", comment="不应绕过重复选课", waived_rules=["DUPLICATE"], reviewer_id="academic-001")
    with pytest.raises(ValueError, match="APPROVAL_RECHECK_FAILED"):
        await service.approve(approval_id="approval-001", comment="重查失败", waived_rules=["CONFLICT"], reviewer_id="academic-001")
    assert (await repository.lock_approval("approval-001")).status == ApprovalStatus.PENDING


@pytest.mark.asyncio
async def test_cancelled_course_and_empty_comment_are_rejected():
    """Cancelled course and empty comment are rejected."""
    repository, _, service = build_approval_service(
        rule_result={"eligible": True, "decision": "ELIGIBLE", "violations": [], "warnings": [], "checked_at": "now"},
        course_status="CANCELLED",
    )
    with pytest.raises(ValueError, match="EMPTY_COMMENT"):
        await service.reject(approval_id="approval-001", comment=" ", reviewer_id="academic-001")
    with pytest.raises(ValueError, match="COURSE_CANCELLED"):
        await service.approve(approval_id="approval-001", comment="无法批准", waived_rules=["CONFLICT"], reviewer_id="academic-001")
    assert (await repository.lock_approval("approval-001")).status == ApprovalStatus.PENDING
