from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class InMemoryStore:
    """第一步的临时数据层。A 后续将其替换为 SQLAlchemy Repository。"""

    users: dict[str, dict[str, Any]] = field(default_factory=dict)
    tokens: dict[str, str] = field(default_factory=dict)
    courses: dict[str, dict[str, Any]] = field(default_factory=dict)
    enrollments: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    waitlists: dict[tuple[str, str], dict[str, Any]] = field(default_factory=dict)
    recommendations: dict[str, dict[str, Any]] = field(default_factory=dict)
    runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    approvals: dict[str, dict[str, Any]] = field(default_factory=dict)
    course_operation_approvals: dict[str, dict[str, Any]] = field(default_factory=dict)
    audits: list[dict[str, Any]] = field(default_factory=list)


def build_store() -> InMemoryStore:
    store = InMemoryStore()
    store.users.update(
        {
            "student-001": {
                "id": "student-001",
                "username": "student",
                "password": "student123",
                "role": "STUDENT",
                "student_no": "S2026001",
            },
            "academic-001": {
                "id": "academic-001",
                "username": "academic",
                "password": "academic123",
                "role": "ACADEMIC",
                "student_no": None,
            },
        }
    )
    store.courses.update(
        {
            "course-101": {
                "id": "course-101",
                "code": "CS101",
                "name": "程序设计基础",
                "teacher_name": "王老师",
                "credits": 3,
                "capacity": 2,
                "status": "OPEN",
                "schedules": [{"weekday": 1, "start_minute": 480, "end_minute": 570, "room": "A101"}],
                "prerequisites": [],
            },
            "course-201": {
                "id": "course-201",
                "code": "AI201",
                "name": "人工智能导论",
                "teacher_name": "李老师",
                "credits": 3,
                "capacity": 1,
                "status": "OPEN",
                "schedules": [{"weekday": 1, "start_minute": 480, "end_minute": 570, "room": "B201"}],
                "prerequisites": ["CS101"],
            },
            "course-301": {
                "id": "course-301",
                "code": "SE301",
                "name": "软件工程实践",
                "teacher_name": "周老师",
                "credits": 2,
                "capacity": 3,
                "status": "OPEN",
                "schedules": [{"weekday": 3, "start_minute": 600, "end_minute": 690, "room": "C301"}],
                "prerequisites": [],
            },
        }
    )
    store.enrollments[("student-001", "course-101")] = {
        "student_id": "student-001",
        "course_id": "course-101",
        "status": "ENROLLED",
        "created_at": utc_now(),
    }
    store.waitlists[("student-001", "course-201")] = {
        "student_id": "student-001",
        "course_id": "course-201",
        "status": "WAITING",
        "position": 1,
        "joined_at": utc_now(),
    }
    return store


STORE = build_store()
