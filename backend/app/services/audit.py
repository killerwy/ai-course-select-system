from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping
from uuid import uuid4
import hashlib

from ..contracts import Role
from ..schemas.admin import AuditRecord


REDACTED = "[REDACTED]"
_SENSITIVE_EXACT_KEYS = {
    "authorization",
    "password",
    "password_hash",
    "api_key",
    "apikey",
    "access_token",
    "refresh_token",
    "client_secret",
    "jwt_secret",
    "deepseek_api_key",
}


def _is_sensitive_key(key: object) -> bool:
    normalized = str(key).strip().lower().replace("-", "_")
    return (
        normalized in _SENSITIVE_EXACT_KEYS
        or normalized.endswith("_token")
        or normalized.endswith("_secret")
    )


def redact_sensitive(value: Any) -> Any:
    """Recursively redact credential-like mapping values before audit persistence."""

    if isinstance(value, Mapping):
        return {
            key: REDACTED if _is_sensitive_key(key) else redact_sensitive(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_sensitive(item) for item in value]
    if isinstance(value, tuple):
        return tuple(redact_sensitive(item) for item in value)
    return value


def compact_request_id(request_id: str, max_length: int = 64) -> str:
    """Keep trace IDs within the audit table limit without losing uniqueness context."""

    value = str(request_id or "")
    if len(value) <= max_length:
        return value
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{value[:max_length - len(digest) - 1]}-{digest}"


def build_audit_record(
    *,
    actor_id: str,
    actor_role: Role,
    action: str,
    resource_type: str,
    resource_id: str,
    request_id: str,
    subject_student_id: str | None = None,
    before_json: Mapping[str, Any] | None = None,
    after_json: Mapping[str, Any] | None = None,
    reason: str | None = None,
    run_id: str | None = None,
    audit_id: str | None = None,
    created_at: datetime | None = None,
) -> AuditRecord:
    """Create a validated, redacted audit record from one state transition."""

    return AuditRecord(
        id=audit_id or f"audit-{uuid4().hex[:12]}",
        actor_id=actor_id,
        subject_student_id=subject_student_id,
        actor_role=actor_role,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        before_json=redact_sensitive(before_json or {}),
        after_json=redact_sensitive(after_json or {}),
        reason=reason,
        run_id=run_id,
        request_id=compact_request_id(request_id),
        created_at=created_at or datetime.now(timezone.utc),
    )
