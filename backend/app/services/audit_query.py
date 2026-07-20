from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from ..contracts import Role
from ..schemas.admin import AuditFilters, AuditRecord


def query_admin_audits(
    records: Iterable[AuditRecord],
    filters: AuditFilters | dict[str, Any] | None = None,
    *,
    actor_role: Role,
) -> tuple[list[AuditRecord], int]:
    """Filter and paginate already-redacted audit records for academic users."""

    if actor_role != Role.ACADEMIC:
        raise PermissionError("FORBIDDEN")
    parsed = filters if isinstance(filters, AuditFilters) else AuditFilters.model_validate(filters or {})
    if parsed.from_ and parsed.to and parsed.from_ > parsed.to:
        raise ValueError("INVALID_TIME_RANGE")

    matched = list(records)

    def keep(record: AuditRecord) -> bool:
        if parsed.course_id and not (record.resource_type == "course" and record.resource_id == parsed.course_id) and record.after_json.get("course_id") != parsed.course_id:
            return False
        if parsed.student_id and record.subject_student_id != parsed.student_id:
            return False
        if parsed.action and record.action != parsed.action:
            return False
        if parsed.run_id and record.run_id != parsed.run_id:
            return False
        if parsed.from_ and record.created_at < parsed.from_:
            return False
        if parsed.to and record.created_at > parsed.to:
            return False
        return True

    matched = [record for record in matched if keep(record)]
    matched.sort(key=lambda record: (record.created_at, record.id), reverse=True)
    total = len(matched)
    start = (parsed.page - 1) * parsed.page_size
    return matched[start : start + parsed.page_size], total

