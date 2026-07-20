from __future__ import annotations

import importlib.util

import pytest

from app.contracts import RecommendationRequest
from app.integrations.deepseek import DeepSeekAdapter
from app.schemas.recommendation import GeneratedRecommendationItem
from app.services.database_store import _generate_recommendations


def test_deepseek_sdk_is_declared_and_client_can_initialize(monkeypatch: pytest.MonkeyPatch) -> None:
    """A configured key must not fall back merely because the optional SDK is missing."""

    assert importlib.util.find_spec("openai") is not None
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key-not-sent")
    monkeypatch.setenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1")
    monkeypatch.setenv("DEEPSEEK_MODEL", "deepseek-chat")

    adapter = DeepSeekAdapter()
    client = adapter._get_client()

    assert client.api_key == "test-key-not-sent"
    assert str(client.base_url).rstrip("/") == "https://api.deepseek.com/v1"


class FakeDeepSeek:
    async def recommend(self, payload, snapshot):
        return [GeneratedRecommendationItem(course_id="course-1", reasons=["符合目标"], uncertainties=["仍需核对课表"])]


class UnavailableDeepSeek:
    async def recommend(self, payload, snapshot):
        from app.integrations.deepseek import DeepSeekUnavailable

        raise DeepSeekUnavailable("test fallback")


@pytest.mark.asyncio
async def test_database_recommendation_status_reflects_provider_result() -> None:
    payload = RecommendationRequest(goals="人工智能", preferences=[])
    snapshot = {"catalog": [{"id": "course-1", "code": "AI101", "name": "人工智能基础"}]}

    _, completed_status, completed_model = await _generate_recommendations(payload, snapshot, FakeDeepSeek())
    _, fallback_status, fallback_model = await _generate_recommendations(payload, snapshot, UnavailableDeepSeek())

    assert (completed_status, completed_model) == ("COMPLETED", "deepseek")
    assert (fallback_status, fallback_model) == ("FALLBACK", "rule_fallback")
