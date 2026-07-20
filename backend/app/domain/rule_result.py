from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class Decision(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    CONFLICT = "CONFLICT"
    PREREQUISITE_MISSING = "PREREQUISITE_MISSING"
    DUPLICATE = "DUPLICATE"
    CAPACITY_FULL = "CAPACITY_FULL"
    COURSE_CLOSED = "COURSE_CLOSED"
    COURSE_CANCELLED = "COURSE_CANCELLED"
    EXCEPTION_REQUIRED = "EXCEPTION_REQUIRED"


@dataclass
class Violation:
    code: str
    message: str
    blocking: bool = True


@dataclass
class RuleResult:
    eligible: bool
    decision: Decision
    violations: list[Violation] = field(default_factory=list)
    warnings: list[Violation] = field(default_factory=list)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def reject(self, decision: Decision, code: str, message: str) -> None:
        self.eligible = False
        self.decision = decision
        self.violations.append(Violation(code, message, True))

    def to_dict(self) -> dict:
        return {
            "eligible": self.eligible,
            "decision": self.decision.value,
            "violations": [vars(item) for item in self.violations],
            "warnings": [vars(item) for item in self.warnings],
            "checked_at": self.checked_at.isoformat(),
        }

