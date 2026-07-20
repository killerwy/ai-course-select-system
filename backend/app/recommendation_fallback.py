import re

from .contracts import RecommendationRequest
from .schemas.recommendation import GeneratedRecommendationItem


def _bigrams(text: str) -> set[str]:
    normalized = re.sub(r"\s+", "", text.casefold())
    return {normalized[index : index + 2] for index in range(max(0, len(normalized) - 1))}


def fallback_recommendations(
    payload: RecommendationRequest,
    courses: list[dict],
) -> list[GeneratedRecommendationItem]:
    """Deterministic, offline-safe ranking used when DeepSeek is unavailable."""

    query_bigrams = _bigrams(" ".join([payload.goals, *payload.preferences]))
    scored: list[tuple[int, str, str, list[str], dict]] = []
    for course in courses:
        course_bigrams = _bigrams(f"{course.get('code', '')}{course.get('name', '')}")
        keyword_hits = len(query_bigrams & course_bigrams)
        reasons = (
            ["课程名称或代码与学习目标/偏好中的关键词相关"]
            if keyword_hits
            else ["课程属于当前开放的候选课程集合"]
        )
        scored.append((keyword_hits * 3, str(course.get("code", "")), str(course["id"]), reasons, course))

    scored.sort(key=lambda item: (-item[0], item[1], item[2]))
    return [
        GeneratedRecommendationItem(
            course_id=course["id"],
            reasons=reasons,
            uncertainties=["当前使用固定规则推荐，最终资格以提交选课时的实时检查为准"],
        )
        for _, _, _, reasons, course in scored[:10]
    ]
