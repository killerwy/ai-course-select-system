from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Role(str, Enum):
    STUDENT = "STUDENT"
    ACADEMIC = "ACADEMIC"


class CourseStatus(str, Enum):
    OPEN = "OPEN"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class EnrollmentStatus(str, Enum):
    ENROLLED = "ENROLLED"
    CONFLICT_REVIEW = "CONFLICT_REVIEW"
    DROPPED = "DROPPED"
    CANCELLED_BY_ADMIN = "CANCELLED_BY_ADMIN"


class WaitlistStatus(str, Enum):
    WAITING = "WAITING"
    PROMOTED = "PROMOTED"
    SKIPPED = "SKIPPED"
    REMOVED = "REMOVED"
    CLOSED = "CLOSED"


class LoginRequest(BaseModel):
    username: str = Field(min_length=1)
    password: str = Field(min_length=1)


class RegisterRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)
    student_no: str = Field(min_length=1, max_length=20)
    major: str = Field(default="", max_length=100)
    grade: int = Field(default=1, ge=1, le=8)


class LoginResponse(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    user: dict


class CourseSchedule(BaseModel):
    weekday: int = Field(ge=1, le=7)
    start_minute: int = Field(ge=0, le=1439)
    end_minute: int = Field(ge=1, le=1440)
    room: str = "TBD"

    @model_validator(mode="after")
    def validate_range(self) -> "CourseSchedule":
        if self.start_minute >= self.end_minute:
            raise ValueError("start_minute 必须小于 end_minute")
        return self


class CourseSummary(BaseModel):
    id: str
    code: str
    name: str
    teacher_name: str = ""
    credits: int
    capacity: int
    enrolled_count: int
    waitlist_count: int
    status: CourseStatus
    schedules: list[CourseSchedule] = Field(default_factory=list)
    prerequisites: list[str] = Field(default_factory=list)


class CourseWriteRequest(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=200)
    teacher_name: str = Field(min_length=1, max_length=100)
    credits: int = Field(gt=0, le=20)
    capacity: int = Field(gt=0, le=10000)
    schedules: list[CourseSchedule] = Field(min_length=1)
    prerequisites: list[str] = Field(default_factory=list, max_length=20)


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goals: str = Field(min_length=1)
    preferences: list[str] = Field(default_factory=list)
    # Opt-in retrieval augmentation.  The default keeps the existing
    # deterministic/DeepSeek recommendation contract unchanged.
    use_rag: bool = False


class RuleViolation(BaseModel):
    code: str
    message: str
    blocking: bool = True


class EligibilitySnapshot(BaseModel):
    eligible: bool
    decision: str
    violations: list[RuleViolation] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    checked_at: str


class RecommendationItem(BaseModel):
    course_id: str
    rank: int
    reasons: list[str] = Field(min_length=1)
    uncertainties: list[str] = Field(min_length=1)
    eligibility: EligibilitySnapshot


class RecommendationSession(BaseModel):
    id: str
    status: Literal["COMPLETED", "FALLBACK", "PENDING"]
    model: str = "rule_fallback"
    rag_status: Literal["NOT_REQUESTED", "USED", "UNAVAILABLE"] = "NOT_REQUESTED"
    rag_message: str | None = None
    items: list[RecommendationItem] = Field(default_factory=list)


class EnrollmentRequestIn(BaseModel):
    course_id: str
    type: Literal["ENROLL", "WAITLIST", "DROP"]


class ExpandRequest(BaseModel):
    capacity_delta: int = Field(gt=0)


class RescheduleRequest(BaseModel):
    schedules: list[CourseSchedule] = Field(min_length=1)


class CancelRequest(BaseModel):
    reason: str = Field(min_length=1)


class CourseChangePreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation: Literal["UPDATE", "EXPAND", "CANCEL"]
    capacity: int | None = Field(default=None, gt=0, le=10000)
    schedules: list[CourseSchedule] | None = Field(default=None, min_length=1)


class ApprovalDecision(BaseModel):
    comment: str = Field(min_length=1)
    waived_rules: list[str] = Field(default_factory=list)
