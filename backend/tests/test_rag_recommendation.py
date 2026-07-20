"""Tests for RAG recommendation integration."""

import pytest

from app.contracts import RecommendationRequest
from app.integrations.rag import RAGResult, RAGUnavailable
from app.schemas.recommendation import GeneratedRecommendationItem
from app.services.course_snapshot import CourseSnapshotService, MemorySnapshotCache
from app.services.recommendation import RecommendationService
from app.store import InMemoryStore


class FakeRAG:
    async def retrieve(self, payload, snapshot):
        return RAGResult(course_ids=["course-b"], context="course-b is relevant evidence")


class UnavailableRAG:
    async def retrieve(self, payload, snapshot):
        raise RAGUnavailable("RAG_DEPENDENCY_MISSING")


class RecordingDeepSeek:
    def __init__(self):
        self.context = None

    async def recommend(self, payload, snapshot, retrieved_context=None):
        self.context = retrieved_context
        course = snapshot["catalog"][0]
        return [GeneratedRecommendationItem(course_id=course["id"], reasons=["matched"], uncertainties=["check timetable"])]


def make_store() -> InMemoryStore:
    return InMemoryStore(
        courses={
            "course-a": {"id": "course-a", "code": "AI101", "name": "人工智能基础", "credits": 3, "capacity": 2, "status": "OPEN", "schedules": [], "prerequisites": []},
            "course-b": {"id": "course-b", "code": "SE201", "name": "软件工程实践", "credits": 3, "capacity": 2, "status": "OPEN", "schedules": [], "prerequisites": []},
        }
    )


@pytest.mark.asyncio
async def test_rag_restricts_prompt_to_retrieved_courses_and_marks_session():
    """RAG restricts prompt to retrieved courses and marks session."""
    deepseek = RecordingDeepSeek()
    service = RecommendationService(
        make_store(),
        deepseek=deepseek,
        snapshot_service=CourseSnapshotService(cache=MemorySnapshotCache()),
        rag=FakeRAG(),
    )

    session = await service.create("student-1", RecommendationRequest(goals="软件工程", use_rag=True))

    assert session.model == "deepseek_rag"
    assert session.rag_status == "USED"
    assert session.items[0].course_id == "course-b"
    assert "course-b" in deepseek.context


@pytest.mark.asyncio
async def test_missing_rag_dependencies_falls_back_without_breaking_recommendations():
    """Missing RAG dependencies falls back without breaking recommendations."""
    deepseek = RecordingDeepSeek()
    service = RecommendationService(
        make_store(),
        deepseek=deepseek,
        snapshot_service=CourseSnapshotService(cache=MemorySnapshotCache()),
        rag=UnavailableRAG(),
    )

    session = await service.create("student-1", RecommendationRequest(goals="人工智能", use_rag=True))

    assert session.model == "deepseek"
    assert session.rag_status == "UNAVAILABLE"
    assert session.rag_message == "RAG_DEPENDENCY_MISSING"
    assert session.items


def test_rag_option_is_part_of_the_strict_request_contract():
    """RAG option is part of the strict request contract."""
    payload = RecommendationRequest.model_validate({"goals": "AI", "preferences": [], "use_rag": True})
    assert payload.use_rag
    with pytest.raises(ValueError):
        RecommendationRequest.model_validate({"goals": "AI", "use_rag": True, "unknown": 1})
