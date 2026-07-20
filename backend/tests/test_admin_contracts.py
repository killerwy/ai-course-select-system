"""Tests for admin schema contracts."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.ports.admin import stable_waitlist_key
from app.schemas.admin import (
    AdminCourseFilters,
    AdminErrorCode,
    ErrorEnvelope,
    RecalculationResult,
    RecalculationRun,
    RunStatus,
    TriggerType,
    error_response,
    success_response,
)
from app.services.audit import REDACTED, build_audit_record, compact_request_id, redact_sensitive


@pytest.fixture
def fixture():
    fixture_path = Path(__file__).parent / "fixtures" / "admin_contract.json"
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def test_fixture_freezes_admin_paths_and_statuses(fixture):
    """Fixture freezes admin paths and statuses."""
    assert fixture["base_url"] == "http://localhost:8000/api/v1"
    assert "/admin/courses" in fixture["admin_paths"]
    assert fixture["run_statuses"] == [status.value for status in RunStatus]
    assert fixture["waitlist_order"] == ["joined_at", "id"]


def test_success_response_uses_common_envelope():
    """Success response uses common envelope format."""
    response = success_response({"id": "run-001"}, "req-001")
    assert set(response) == {"data", "meta"}
    assert response["meta"]["request_id"] == "req-001"


def test_error_response_uses_common_envelope():
    """Error response uses common envelope format."""
    response = error_response(AdminErrorCode.INVALID_FILTER, "筛选条件无效", "req-002")
    parsed = ErrorEnvelope.model_validate(response)
    assert parsed.error.code == "INVALID_FILTER"
    assert parsed.meta.request_id == "req-002"


def test_recalculation_result_requires_reason_and_run_status():
    """RecalculationResult requires reason and run status."""
    result = RecalculationResult(
        entity_type="WAITLIST",
        entity_id="wait-001",
        old_status="WAITING",
        new_status="SKIPPED",
        reason_code="TIME_CONFLICT",
    )
    run = RecalculationRun(
        id="run-001",
        course_id="course-201",
        trigger_type=TriggerType.EXPAND,
        status=RunStatus.SUCCEEDED,
        results=[result],
    )
    assert run.results[0].reason_code == "TIME_CONFLICT"
    assert run.status == RunStatus.SUCCEEDED


def test_waitlist_order_is_joined_at_then_id():
    """Waitlist order is joined_at then id."""
    first = {"id": "wait-002", "joined_at": "2026-07-16T06:00:00+00:00"}
    second = {"id": "wait-001", "joined_at": "2026-07-16T06:00:00+00:00"}
    assert stable_waitlist_key(second) < stable_waitlist_key(first)


def test_filter_page_size_boundary_is_rejected():
    """Filter page size boundary is rejected."""
    with pytest.raises(ValidationError):
        AdminCourseFilters(page_size=101)


def test_result_without_reason_is_rejected():
    """Result without reason is rejected."""
    with pytest.raises(ValidationError):
        RecalculationResult(entity_type="WAITLIST", entity_id="wait-001")


def test_unknown_run_status_is_rejected():
    """Unknown run status is rejected."""
    with pytest.raises(ValidationError):
        RecalculationRun(
            id="run-001",
            course_id="course-201",
            trigger_type=TriggerType.MANUAL,
            status="DONE",
        )


def test_audit_redacts_nested_credentials_but_keeps_business_fields():
    """Audit redacts nested credentials but keeps business fields."""
    payload = {
        "status": "ENROLLED",
        "credentials": {
            "authorization": "Bearer demo-token",
            "password": "do-not-log",
            "nested": [{"api_key": "secret-value", "course_id": "course-201"}],
        },
    }
    redacted = redact_sensitive(payload)
    assert redacted["status"] == "ENROLLED"
    assert redacted["credentials"]["authorization"] == REDACTED
    assert redacted["credentials"]["nested"][0]["api_key"] == REDACTED
    assert redacted["credentials"]["nested"][0]["course_id"] == "course-201"


def test_audit_record_contains_context_and_redacted_snapshots():
    """Audit record contains context and redacted snapshots."""
    record = build_audit_record(
        actor_id="academic-001",
        actor_role="ACADEMIC",
        action="WAITLIST_PROMOTED",
        resource_type="waitlist_entry",
        resource_id="wait-001",
        request_id="req-003",
        subject_student_id="student-001",
        before_json={"status": "WAITING", "access_token": "secret"},
        after_json={"status": "PROMOTED"},
    )
    assert record.request_id == "req-003"
    assert record.before_json["access_token"] == REDACTED
    assert record.after_json["status"] == "PROMOTED"


def test_audit_record_rejects_missing_request_context():
    """Audit record rejects missing request context."""
    with pytest.raises(ValidationError):
        build_audit_record(
            actor_id="academic-001",
            actor_role="ACADEMIC",
            action="COURSE_EXPANDED",
            resource_type="course",
            resource_id="course-201",
            request_id="",
        )


def test_audit_request_id_is_bounded_for_uuid_student_and_course_ids():
    """Audit request ID is bounded for UUID student and course IDs."""
    long_id = "student:" + ("a" * 36) + ":" + ("b" * 36)
    compacted = compact_request_id(long_id)
    assert len(compacted) <= 64
    assert compacted == compact_request_id(long_id)
