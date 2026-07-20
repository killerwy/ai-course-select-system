from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .rule_result import Decision, RuleResult


@dataclass
class ScheduleSlot:
    weekday: int
    start_minute: int
    end_minute: int


@dataclass
class Prerequisite:
    course_id: str
    min_grade: str = "D"


@dataclass
class CourseRuleInput:
    rule_type: str
    config: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


@dataclass
class CourseInput:
    id: str
    status: str
    capacity: int
    credits: int
    schedules: list[ScheduleSlot] = field(default_factory=list)
    prerequisites: list[Prerequisite] = field(default_factory=list)
    rules: list[CourseRuleInput] = field(default_factory=list)


@dataclass
class EnrollmentRecord:
    course_id: str
    status: str


@dataclass
class CompletedCourse:
    course_id: str
    grade: str = "A"


@dataclass
class StudentProfile:
    grade: int = 1
    major: str = ""
    credits_earned: int = 0


GRADE_RANK = {"A+": 1, "A": 2, "A-": 3, "B+": 4, "B": 5, "B-": 6, "C+": 7, "C": 8, "C-": 9, "D": 10, "F": 11}


def _overlaps(left: ScheduleSlot, right: ScheduleSlot) -> bool:
    return left.weekday == right.weekday and left.start_minute < right.end_minute and right.start_minute < left.end_minute


class RuleEngine:
    """Pure deterministic rule engine migrated from group member A."""

    def check(
        self,
        course: CourseInput,
        student_enrollments: list[EnrollmentRecord],
        student_completed: list[CompletedCourse],
        student_profile: StudentProfile,
        request_type: str,
        enrolled_schedules: list[ScheduleSlot] | None = None,
        existing_waitlist_for_course: bool = False,
        waived_rules: list[str] | None = None,
    ) -> RuleResult:
        waived = set(waived_rules or [])
        result = RuleResult(True, Decision.ELIGIBLE)
        if course.status == "CANCELLED":
            result.reject(Decision.COURSE_CANCELLED, "COURSE_CANCELLED", "课程已取消")
            return result
        if course.status != "OPEN":
            result.reject(Decision.COURSE_CLOSED, "COURSE_CLOSED", "课程当前不可选")
            return result

        if "DUPLICATE" not in waived:
            duplicate = any(item.course_id == course.id and item.status in {"ENROLLED", "CONFLICT_REVIEW"} for item in student_enrollments)
            if duplicate or existing_waitlist_for_course:
                result.reject(Decision.DUPLICATE, "DUPLICATE", "已存在有效选课或候补记录")
                return result

        if "PREREQUISITE_MISSING" not in waived and "PREREQUISITE" not in waived:
            grades = {item.course_id: item.grade for item in student_completed}
            for prereq in course.prerequisites:
                grade = grades.get(prereq.course_id)
                if grade is None or GRADE_RANK.get(grade, 11) > GRADE_RANK.get(prereq.min_grade, 11):
                    result.reject(Decision.PREREQUISITE_MISSING, "PREREQUISITE_MISSING", f"缺少先修课程 {prereq.course_id}")
                    return result

        if "TIME_CONFLICT" not in waived and "CONFLICT" not in waived:
            for target in course.schedules:
                if any(_overlaps(target, existing) for existing in (enrolled_schedules or [])):
                    result.reject(Decision.CONFLICT, "TIME_CONFLICT", "与已选课程时间冲突")
                    return result

        for rule in course.rules:
            if not rule.enabled:
                continue
            if rule.rule_type == "GRADE" and student_profile.grade < int(rule.config.get("min_grade", 0)):
                result.reject(Decision.EXCEPTION_REQUIRED, "GRADE_NOT_MET", "年级不满足课程要求")
                return result
            if rule.rule_type == "MAJOR" and student_profile.major not in rule.config.get("allowed_majors", [student_profile.major]):
                result.reject(Decision.EXCEPTION_REQUIRED, "MAJOR_NOT_MET", "专业不满足课程要求")
                return result
        return result

