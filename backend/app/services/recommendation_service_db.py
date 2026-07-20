"""Recommendation service for database mode."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import get_settings
from ..integrations.deepseek import DeepSeekAdapter, DeepSeekUnavailable
from ..integrations.rag import DEFAULT_RAG, LocalCourseRAG, RAGUnavailable
from ..models import (
    Course,
    Enrollment,
    RecommendationItem,
    RecommendationSession,
)
from ..recommendation_fallback import fallback_recommendations
from .course_query_service import course_summary
from .enrollment_service import _write_audit, check_enrollment
from ..utils import ACTIVE_ENROLLMENT_STATUSES, _json_dump, _json_load, _utcnow


ACTIVE_ENROLLMENT = ACTIVE_ENROLLMENT_STATUSES


async def _generate_recommendations_details(
    payload: Any,
    snapshot: dict,
    adapter: DeepSeekAdapter | None = None,
    rag: LocalCourseRAG | None = None,
) -> tuple[list[Any], str, str, str, str | None]:
    """Generate recommendations and expose the RAG state for the API response."""

    use_rag = bool(getattr(payload, "use_rag", False))
    rag_status = "NOT_REQUESTED"
    rag_message: str | None = None
    prompt_snapshot = snapshot
    rag_context: str | None = None
    if use_rag:
        try:
            rag_result = await (rag or DEFAULT_RAG).retrieve(payload, snapshot)
            course_by_id = {course["id"]: course for course in snapshot.get("catalog", [])}
            rag_courses = [course_by_id[course_id] for course_id in rag_result.course_ids if course_id in course_by_id]
            if not rag_courses:
                raise RAGUnavailable("RAG_NO_MATCH")
            prompt_snapshot = {**snapshot, "catalog": rag_courses}
            rag_context = rag_result.context
            rag_status = "USED"
        except RAGUnavailable as exc:
            rag_status = "UNAVAILABLE"
            rag_message = str(exc)

    try:
        if rag_context:
            generated_items = await (adapter or DeepSeekAdapter()).recommend(
                payload,
                prompt_snapshot,
                retrieved_context=rag_context,
            )
            model_name = "deepseek_rag"
        else:
            generated_items = await (adapter or DeepSeekAdapter()).recommend(payload, snapshot)
            model_name = "deepseek"
        return generated_items, "COMPLETED", model_name, rag_status, rag_message
    except DeepSeekUnavailable:
        if use_rag and rag_status == "USED":
            rag_status = "UNAVAILABLE"
            rag_message = "RAG_LLM_UNAVAILABLE"
        return fallback_recommendations(payload, snapshot.get("catalog", [])), "FALLBACK", "rule_fallback", rag_status, rag_message


async def _generate_recommendations(payload: Any, snapshot: dict, adapter: DeepSeekAdapter | None = None) -> tuple[list[Any], str, str]:
    """Backward-compatible three-value helper used by existing tests/callers."""

    generated, status, model, _, _ = await _generate_recommendations_details(payload, snapshot, adapter=adapter)
    return generated, status, model


async def create_recommendation(session: AsyncSession, student_id: str, payload: Any) -> dict:
    courses = list(
        (
            await session.execute(
                select(Course)
                .where(Course.status == "OPEN")
                .options(selectinload(Course.schedules), selectinload(Course.prerequisites))
                .order_by(Course.code)
            )
        ).scalars().unique().all()
    )
    catalog = [await course_summary(session, course) for course in courses]
    selected_ids = {
        item.course_id
        for item in (
            await session.execute(
                select(Enrollment).where(
                    Enrollment.student_id == student_id,
                    Enrollment.status.in_(ACTIVE_ENROLLMENT),
                )
            )
        ).scalars().all()
    }
    snapshot = {
        "student_id": student_id,
        "catalog": catalog,
        "selected_courses": [course for course in catalog if course["id"] in selected_ids],
        "generated_at": _utcnow().isoformat(),
    }
    generated_items, recommendation_status, model_name, rag_status, rag_message = await _generate_recommendations_details(payload, snapshot)
    course_by_id = {course["id"]: course for course in catalog}
    rec_session = RecommendationSession(
        student_id=student_id,
        input_json=_json_dump(payload.model_dump(mode="json")),
        model=model_name,
        status=recommendation_status,
    )
    session.add(rec_session)
    await session.flush()
    items: list[dict] = []
    for rank, generated in enumerate(generated_items, start=1):
        course = course_by_id.get(generated.course_id)
        if course is None:
            continue
        reasons = [text.strip() for text in generated.reasons]
        uncertainties = [text.strip() for text in generated.uncertainties]
        eligibility = await check_enrollment(session, student_id, course["id"], ignore_target_waitlist=False)
        if eligibility.get("eligible") and course.get("enrolled_count", 0) >= course.get("capacity", 0):
            eligibility = {
                **eligibility,
                "eligible": False,
                "decision": "WAITLIST_ALLOWED",
                "violations": [{"code": "CAPACITY_FULL", "message": "课程已满，可加入候补", "blocking": True}],
            }
        session.add(
            RecommendationItem(
                session_id=rec_session.id,
                course_id=course["id"],
                rank=rank,
                reasons_json=_json_dump(reasons),
                uncertainties_json=_json_dump(uncertainties),
                eligibility_json=_json_dump(eligibility),
            )
        )
        items.append({"course_id": course["id"], "rank": rank, "reasons": reasons, "uncertainties": uncertainties, "eligibility": eligibility})
    await _write_audit(
        session,
        actor_id=student_id,
        actor_role="STUDENT",
        action="RECOMMENDATION_CREATED",
        resource_type="recommendation_session",
        resource_id=rec_session.id,
        request_id=f"recommendation:{rec_session.id}",
        subject_student_id=student_id,
    )
    return {
        "id": rec_session.id,
        "status": recommendation_status,
        "model": model_name,
        "rag_status": rag_status,
        "rag_message": rag_message,
        "items": items,
    }


async def get_recommendation(session: AsyncSession, student_id: str, session_id: str) -> dict | None:
    record = (
        await session.execute(
            select(RecommendationSession)
            .where(RecommendationSession.id == session_id, RecommendationSession.student_id == student_id)
            .options(selectinload(RecommendationSession.items))
        )
    ).scalar_one_or_none()
    if record is None:
        return None
    input_payload = _json_load(record.input_json, {})
    rag_requested = bool(input_payload.get("use_rag"))
    rag_status = "USED" if record.model == "deepseek_rag" else ("UNAVAILABLE" if rag_requested else "NOT_REQUESTED")
    return {
        "id": record.id,
        "status": record.status,
        "model": record.model,
        "rag_status": rag_status,
        "rag_message": None,
        "items": [
            {"course_id": item.course_id, "rank": item.rank, "reasons": _json_load(item.reasons_json, []), "uncertainties": _json_load(item.uncertainties_json, []), "eligibility": _json_load(item.eligibility_json, {})}
            for item in sorted(record.items, key=lambda value: (value.rank, value.id))
        ],
    }
