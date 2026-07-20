"""Tests for student web recommendation integration."""

import pytest

from app.contracts import RecommendationRequest
from app.integrations.deepseek import DeepSeekUnavailable
from app.services.course_snapshot import CourseSnapshotService, MemorySnapshotCache
from app.services.recommendation import RecommendationService
from app.store import InMemoryStore


@pytest.mark.asyncio
async def test_fallback_recommendation_reads_snapshot_and_marks_conflict():
    """Fallback recommendation reads snapshot and marks conflict."""
    store = InMemoryStore(
        courses={
            "course-a": {
                "id": "course-a", "code": "AI101", "name": "人工智能基础", "credits": 3,
                "capacity": 2, "status": "OPEN",
                "schedules": [{"weekday": 1, "start_minute": 480, "end_minute": 540, "room": "A"}],
                "prerequisites": [],
            },
            "course-b": {
                "id": "course-b", "code": "SE201", "name": "软件工程", "credits": 3,
                "capacity": 2, "status": "OPEN",
                "schedules": [{"weekday": 1, "start_minute": 500, "end_minute": 560, "room": "B"}],
                "prerequisites": [],
            },
        },
        enrollments={("student-1", "course-a"): {"student_id": "student-1", "course_id": "course-a", "status": "ENROLLED"}},
    )
    cache = MemorySnapshotCache()

    class OfflineDeepSeek:
        async def recommend(self, payload, snapshot):
            raise DeepSeekUnavailable("offline test")

    service = RecommendationService(
        store,
        deepseek=OfflineDeepSeek(),
        snapshot_service=CourseSnapshotService(cache=cache),
    )
    session = await service.create("student-1", RecommendationRequest(goals="人工智能", preferences=["实践"]))

    assert session.status == "FALLBACK"
    assert session.items[0].course_id == "course-a"
    assert session.items[0].eligibility.decision == "DUPLICATE"
    assert cache.values["course-snapshot:student-1"]["selected_courses"]


def test_extra_recommendation_inputs_are_rejected_by_contract():
    """Extra recommendation inputs are rejected by contract."""
    with pytest.raises(ValueError):
        RecommendationRequest.model_validate({"goals": "AI", "completed_course_ids": []})
