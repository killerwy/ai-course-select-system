from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _json_load(raw: str | None, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return default


def _json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str, separators=(",", ":"))


ALLOWED_WAIVED_RULES = {"PREREQUISITE_MISSING", "CONFLICT", "TIME_CONFLICT"}
ACTIVE_ENROLLMENT_STATUSES = {"ENROLLED", "CONFLICT_REVIEW"}


def schedules_overlap(left: list[Mapping[str, Any]], right: list[Mapping[str, Any]]) -> bool:
    for first in left:
        for second in right:
            if int(first.get("weekday", 0)) != int(second.get("weekday", 0)):
                continue
            if int(first.get("start_minute", 0)) < int(second.get("end_minute", 0)) and int(second.get("start_minute", 0)) < int(first.get("end_minute", 0)):
                return True
    return False


def validate_schedules(schedules: list[Mapping[str, Any]]) -> None:
    if not schedules:
        raise ValueError("INVALID_SCHEDULE")
    normalized: list[tuple[int, int, int]] = []
    for item in schedules:
        weekday = int(item.get("weekday", 0))
        start = int(item.get("start_minute", -1))
        end = int(item.get("end_minute", -1))
        if not 1 <= weekday <= 7 or not 0 <= start < end <= 1440:
            raise ValueError("INVALID_SCHEDULE")
        normalized.append((weekday, start, end))
    for index, left in enumerate(normalized):
        for right in normalized[index + 1 :]:
            if left[0] == right[0] and left[1] < right[2] and right[1] < left[2]:
                raise ValueError("INVALID_SCHEDULE")
