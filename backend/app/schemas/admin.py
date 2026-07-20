from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

from ..contracts import CourseStatus, Role


class RunStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class TriggerType(str, Enum):
    EXPAND = "EXPAND"
    RESCHEDULE = "RESCHEDULE"
    CANCEL = "CANCEL"
    MANUAL = "MANUAL"
    COURSE_UPDATE = "COURSE_UPDATE"


class ApprovalStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class CourseOperationType(str, Enum):
    CREATE = "CREATE"
    UPDATE = "UPDATE"
    CANCEL = "CANCEL"


class AdminErrorCode(str, Enum):
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    COURSE_NOT_FOUND = "COURSE_NOT_FOUND"
    RUN_NOT_FOUND = "RUN_NOT_FOUND"
    APPROVAL_NOT_FOUND = "APPROVAL_NOT_FOUND"
    COURSE_OPERATION_NOT_FOUND = "COURSE_OPERATION_NOT_FOUND"
    COURSE_OPERATION_NOT_PENDING = "COURSE_OPERATION_NOT_PENDING"
    COURSE_OPERATION_PENDING = "COURSE_OPERATION_PENDING"
    COURSE_CANCELLED = "COURSE_CANCELLED"
    COURSE_ALREADY_CANCELLED = "COURSE_ALREADY_CANCELLED"
    CONCURRENT_MODIFICATION = "CONCURRENT_MODIFICATION"
    RUN_ALREADY_ACTIVE = "RUN_ALREADY_ACTIVE"
    APPROVAL_RECHECK_FAILED = "APPROVAL_RECHECK_FAILED"
    APPROVAL_RULE_NOT_ALLOWED = "APPROVAL_RULE_NOT_ALLOWED"
    INVALID_CAPACITY_DELTA = "INVALID_CAPACITY_DELTA"
    INVALID_SCHEDULE = "INVALID_SCHEDULE"
    EMPTY_REASON = "EMPTY_REASON"
    EMPTY_COMMENT = "EMPTY_COMMENT"
    INVALID_FILTER = "INVALID_FILTER"
    INVALID_TIME_RANGE = "INVALID_TIME_RANGE"
    RECALCULATION_FAILED = "RECALCULATION_FAILED"
    AUDIT_PAYLOAD_INVALID = "AUDIT_PAYLOAD_INVALID"
    COURSE_ALREADY_EXISTS = "COURSE_ALREADY_EXISTS"
    PREREQUISITE_NOT_FOUND = "PREREQUISITE_NOT_FOUND"
    INVALID_IDEMPOTENCY_KEY = "INVALID_IDEMPOTENCY_KEY"


class ResponseMeta(BaseModel):
    request_id: str = Field(min_length=1)
    page: int | None = Field(default=None, ge=1)
    page_size: int | None = Field(default=None, ge=1, le=100)
    total: int | None = Field(default=None, ge=0)


class SuccessEnvelope(BaseModel):
    data: Any
    meta: ResponseMeta


class ErrorBody(BaseModel):
    code: str = Field(min_length=1)
    message: str = Field(min_length=1)
    details: list[dict[str, Any]] = Field(default_factory=list)


class ErrorEnvelope(BaseModel):
    error: ErrorBody
    meta: ResponseMeta


class RecalculationResult(BaseModel):
    entity_type: Literal["COURSE", "ENROLLMENT", "WAITLIST"]
    entity_id: str = Field(min_length=1)
    student_id: str | None = None
    old_status: str | None = None
    new_status: str | None = None
    reason_code: str = Field(min_length=1)
    details: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime | None = None


class RecalculationSummary(BaseModel):
    checked: int = Field(default=0, ge=0)
    promoted: int = Field(default=0, ge=0)
    skipped: int = Field(default=0, ge=0)
    conflicts: int = Field(default=0, ge=0)
    waiting: int = Field(default=0, ge=0)
    errors: int = Field(default=0, ge=0)


class RecalculationRun(BaseModel):
    id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    trigger_type: TriggerType
    operator_id: str | None = None
    status: RunStatus
    summary: RecalculationSummary = Field(default_factory=RecalculationSummary)
    results: list[RecalculationResult] = Field(default_factory=list)
    started_at: datetime | None = None
    finished_at: datetime | None = None
    error: ErrorBody | None = None


class ApprovalRecord(BaseModel):
    id: str = Field(min_length=1)
    request_id: str | None = None
    enrollment_id: str | None = None
    student_id: str = Field(min_length=1)
    course_id: str = Field(min_length=1)
    status: ApprovalStatus
    rule_violations: list[str] = Field(default_factory=list)
    waived_rules: list[str] = Field(default_factory=list)
    reviewer_id: str | None = None
    comment: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class AuditRecord(BaseModel):
    id: str = Field(min_length=1)
    actor_id: str = Field(min_length=1)
    subject_student_id: str | None = None
    actor_role: Role
    action: str = Field(min_length=1)
    resource_type: str = Field(min_length=1)
    resource_id: str = Field(min_length=1)
    before_json: dict[str, Any] = Field(default_factory=dict)
    after_json: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None
    run_id: str | None = None
    request_id: str = Field(min_length=1)
    created_at: datetime


class AdminCourseFilters(BaseModel):
    status: CourseStatus | None = None
    keyword: str | None = Field(default=None, max_length=100)
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class ApprovalFilters(BaseModel):
    status: ApprovalStatus | None = None
    course_id: str | None = None
    student_id: str | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)


class AuditFilters(BaseModel):
    course_id: str | None = None
    student_id: str | None = None
    action: str | None = None
    run_id: str | None = None
    from_: datetime | None = Field(default=None, alias="from")
    to: datetime | None = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)

    model_config = {"populate_by_name": True}


def success_response(data: Any, request_id: str, **pagination: int) -> dict[str, Any]:
    """Build the frozen success envelope without duplicating response rules."""

    return SuccessEnvelope(
        data=data,
        meta=ResponseMeta(request_id=request_id, **pagination),
    ).model_dump(mode="json")


def error_response(
    code: AdminErrorCode | str,
    message: str,
    request_id: str,
    details: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build the frozen error envelope for router exception translation."""

    return ErrorEnvelope(
        error=ErrorBody(
            code=code.value if isinstance(code, AdminErrorCode) else code,
            message=message,
            details=details or [],
        ),
        meta=ResponseMeta(request_id=request_id),
    ).model_dump(mode="json")
