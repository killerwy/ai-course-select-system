from datetime import datetime
from typing import Any, Mapping, Protocol, TypedDict

from ..schemas.admin import ApprovalRecord, AuditRecord, RecalculationRun


class RuleViolation(TypedDict, total=False):
    code: str
    message: str
    blocking: bool


class RuleResult(TypedDict):
    eligible: bool
    decision: str
    violations: list[RuleViolation]
    warnings: list[RuleViolation]
    checked_at: str


class RequestContext(TypedDict, total=False):
    actor_id: str
    actor_role: str
    request_id: str
    run_id: str


class ApprovalFilters(TypedDict, total=False):
    status: str
    course_id: str
    student_id: str
    page: int
    page_size: int


class AuditFilters(TypedDict, total=False):
    course_id: str
    student_id: str
    action: str
    run_id: str
    from_: datetime
    to: datetime
    page: int
    page_size: int


class RuleChecker(Protocol):
    async def check_enrollment(
        self,
        student_id: str,
        course_id: str,
        *,
        waived_rules: set[str] | None = None,
    ) -> RuleResult:
        ...


class AdminRepository(Protocol):
    async def lock_course(self, course_id: str, expected_version: int | None = None) -> Mapping[str, Any]:
        ...

    async def update_course(self, course: Mapping[str, Any]) -> None:
        ...

    async def list_enrollments(self, course_id: str) -> list[Mapping[str, Any]]:
        ...

    async def list_waiting(self, course_id: str) -> list[Mapping[str, Any]]:
        """Return WAITING entries in stable joined_at, id order."""

        ...

    async def promote_waitlist(self, entry_id: str, student_id: str, course_id: str) -> Mapping[str, Any]:
        ...

    async def skip_waitlist(self, entry_id: str, reason_code: str, details: Mapping[str, Any]) -> Mapping[str, Any]:
        ...

    async def renumber_waitlist(self, course_id: str) -> None:
        ...

    async def get_run(self, run_id: str) -> RecalculationRun | None:
        ...

    async def create_run(self, run: RecalculationRun) -> None:
        ...

    async def update_run(self, run_id: str, patch: Mapping[str, Any]) -> None:
        ...

    async def list_approvals(self, filters: ApprovalFilters) -> list[ApprovalRecord]:
        ...

    async def lock_approval(self, approval_id: str) -> ApprovalRecord:
        ...

    async def update_approval(self, approval_id: str, patch: Mapping[str, Any]) -> ApprovalRecord:
        ...

    async def query_audits(self, filters: AuditFilters) -> list[AuditRecord]:
        ...


class AuditWriter(Protocol):
    async def append(self, record: AuditRecord) -> AuditRecord:
        ...


def stable_waitlist_key(entry: Mapping[str, Any]) -> tuple[str, str]:
    """Return the only allowed ordering key for candidate processing."""

    return (str(entry.get("joined_at", "")), str(entry.get("id", "")))

