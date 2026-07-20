"""Shared SQLAlchemy application service for student and academic routes.

This module is imported only when ``APP_STORAGE=mysql``.  It adapts group A's
database/domain implementation to the frozen group C HTTP contract, including
``SUCCEEDED`` recalculation runs and auditable approval decisions.

This file re-exports functions from the split modules for backward compatibility.
New code should import directly from the specific modules.
"""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..utils import ACTIVE_ENROLLMENT_STATUSES, ALLOWED_WAIVED_RULES, _utcnow

# Re-export from split modules for backward compatibility
from .auth_service import (  # noqa: F401
    authenticate,
    create_access_token,
    decode_access_token,
    get_user_from_token,
    hash_password,
    register_student,
    verify_password,
)
from .course_query_service import (  # noqa: F401
    _course,
    _course_input,
    course_summary,
    list_course_summaries,
)
from .enrollment_service import (  # noqa: F401
    _upsert_enrollment,
    _write_audit,
    check_enrollment,
    list_student_audits,
    list_student_enrollments,
    list_student_schedule,
    list_student_waitlists,
    process_enrollment_request,
)
from .recommendation_service_db import (  # noqa: F401
    _generate_recommendations,
    _generate_recommendations_details,
    create_recommendation,
    get_recommendation,
)

ACTIVE_ENROLLMENT = ACTIVE_ENROLLMENT_STATUSES
TERMINAL_RUN = {"SUCCEEDED", "FAILED"}


def _json_load(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return default


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))
