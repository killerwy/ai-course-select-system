"""Tests for admin router endpoints."""

import json

import pytest
from fastapi import BackgroundTasks
from starlette.requests import Request

from app.contracts import ExpandRequest
from app.routers.admin import RULE_CHECKER, expand_course, get_run
from app.store import STORE


def make_request(request_id: str) -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/admin/courses/course-router-test/expand",
            "headers": [(b"x-request-id", request_id.encode())],
        }
    )


@pytest.fixture(autouse=True)
def setup_and_teardown():
    """Setup and teardown test data in global STORE."""
    course_id = "course-router-test"
    old_course = STORE.courses.get(course_id)
    STORE.courses[course_id] = {
        "id": course_id,
        "code": "RT001",
        "name": "Router Test",
        "credits": 1,
        "capacity": 1,
        "status": "OPEN",
        "schedules": [{"weekday": 2, "start_minute": 600, "end_minute": 660, "room": "T101"}],
        "prerequisites": [],
    }
    audit_count = len(STORE.audits)
    yield
    if old_course is None:
        STORE.courses.pop(course_id, None)
    else:
        STORE.courses[course_id] = old_course
    STORE.audits[:] = STORE.audits[:audit_count]


@pytest.mark.asyncio
async def test_expand_enqueues_and_poll_returns_terminal_run():
    """Expand enqueues a task and poll returns terminal run."""
    course_id = "course-router-test"
    tasks = BackgroundTasks()
    response = await expand_course(
        make_request("router-expand-001"),
        tasks,
        course_id,
        ExpandRequest(capacity_delta=1),
        None,
        {"id": "academic-001", "role": "ACADEMIC"},
        "router-expand-key",
    )
    assert response["meta"]["request_id"] == "router-expand-001"
    run_id = response["data"]["run"]["id"]
    assert response["data"]["run"]["status"] == "PENDING"
    await tasks()
    polled = await get_run(make_request("router-poll-001"), run_id, {"id": "academic-001", "role": "ACADEMIC"})
    assert polled["data"]["status"] == "SUCCEEDED"
    assert STORE.courses[course_id]["capacity"] == 2


@pytest.mark.asyncio
async def test_missing_course_uses_error_envelope():
    """Missing course returns error envelope with 404."""
    tasks = BackgroundTasks()
    response = await expand_course(
        make_request("router-error-001"),
        tasks,
        "course-does-not-exist",
        ExpandRequest(capacity_delta=1),
        None,
        {"id": "academic-001", "role": "ACADEMIC"},
        "router-error-key",
    )
    assert response.status_code == 404
    body = json.loads(response.body)
    assert body["error"]["code"] == "COURSE_NOT_FOUND"
    assert body["meta"]["request_id"] == "router-error-001"


@pytest.mark.asyncio
async def test_baseline_checker_does_not_treat_conflict_review_as_duplicate():
    """Baseline checker does not treat CONFLICT_REVIEW as duplicate."""
    course_id = "course-router-test"
    key = ("student-router-test", course_id)
    STORE.enrollments[key] = {"student_id": key[0], "course_id": key[1], "status": "CONFLICT_REVIEW"}
    try:
        result = await RULE_CHECKER.check_enrollment(key[0], course_id, waived_rules={"CONFLICT"})
        assert result["eligible"]
    finally:
        STORE.enrollments.pop(key, None)
