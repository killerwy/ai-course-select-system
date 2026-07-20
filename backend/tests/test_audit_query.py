"""Tests for audit query service."""

from datetime import datetime, timezone

import pytest

from app.contracts import Role
from app.schemas.admin import AuditFilters
from app.services.audit import build_audit_record
from app.services.audit_query import query_admin_audits


def audit(action, student, minute, run_id="run-001"):
    return build_audit_record(
        actor_id="academic-001",
        actor_role=Role.ACADEMIC,
        action=action,
        resource_type="waitlist_entry",
        resource_id=f"wait-{minute}",
        subject_student_id=student,
        request_id=f"req-{minute}",
        run_id=run_id,
        created_at=datetime(2026, 7, 16, 6, minute, tzinfo=timezone.utc),
    )


def test_filters_sorts_and_paginates():
    """Query filters, sorts, and paginates audit records."""
    records = [
        audit("WAITLIST_SKIPPED", "student-001", 1),
        audit("WAITLIST_PROMOTED", "student-001", 2),
        audit("WAITLIST_PROMOTED", "student-002", 3, "run-002"),
    ]
    page, total = query_admin_audits(records, {"student_id": "student-001", "page": 1, "page_size": 1}, actor_role=Role.ACADEMIC)
    assert total == 2
    assert len(page) == 1
    assert page[0].action == "WAITLIST_PROMOTED"


def test_empty_filter_returns_empty_page_and_zero_total():
    """Empty filter returns empty page and zero total."""
    page, total = query_admin_audits([], AuditFilters(), actor_role=Role.ACADEMIC)
    assert page == []
    assert total == 0


def test_invalid_time_range_and_non_academic_are_rejected():
    """Invalid time range and non-academic role are rejected."""
    records = [audit("WAITLIST_SKIPPED", "student-001", 1)]
    with pytest.raises(ValueError, match="INVALID_TIME_RANGE"):
        query_admin_audits(records, {"from": "2026-07-17T00:00:00Z", "to": "2026-07-16T00:00:00Z"}, actor_role=Role.ACADEMIC)
    with pytest.raises(PermissionError, match="FORBIDDEN"):
        query_admin_audits(records, actor_role=Role.STUDENT)
