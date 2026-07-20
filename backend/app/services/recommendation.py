from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from ..contracts import EligibilitySnapshot, RecommendationItem, RecommendationRequest, RecommendationSession, RuleViolation
from ..integrations.deepseek import DeepSeekAdapter, DeepSeekUnavailable
from ..integrations.rag import DEFAULT_RAG, LocalCourseRAG, RAGUnavailable
from ..recommendation_fallback import fallback_recommendations
from ..store import InMemoryStore
from .course_snapshot import CourseSnapshotService, SNAPSHOT_SERVICE, conflicting_selected_courses


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def current_snapshot_eligibility(student_id: str, course: dict, snapshot: dict, store: InMemoryStore) -> EligibilitySnapshot:
    violations: list[RuleViolation] = []
    decision = "ELIGIBLE"
    if course.get("status") != "OPEN":
        decision = "COURSE_CANCELLED" if course.get("status") == "CANCELLED" else "COURSE_CLOSED"
        violations.append(RuleViolation(code=decision, message="课程当前不可选"))
    else:
        key = (student_id, course["id"])
        enrollment = store.enrollments.get(key)
        waitlist = store.waitlists.get(key)
        if enrollment and enrollment.get("status") in {"ENROLLED", "CONFLICT_REVIEW"}:
            decision = "DUPLICATE"
            violations.append(RuleViolation(code=decision, message="已经选过该课程"))
        elif waitlist and waitlist.get("status") == "WAITING":
            decision = "DUPLICATE"
            violations.append(RuleViolation(code=decision, message="已经在该课程候补队列中"))
    if not violations:
        selected_codes = {selected.get("code") for selected in snapshot.get("selected_courses", [])}
        missing = [code for code in course.get("prerequisites", []) if code not in selected_codes]
        if missing:
            decision = "PREREQUISITE_MISSING"
            violations.append(RuleViolation(code=decision, message=f"缺少先修课程：{'、'.join(missing)}"))
    if not violations:
        conflicts = conflicting_selected_courses(snapshot, course["id"])
        if conflicts:
            decision = "CONFLICT"
            violations.append(RuleViolation(code=decision, message=f"与已选课程 {'、'.join(item['code'] for item in conflicts)} 时间冲突"))
    if not violations and course.get("enrolled_count", 0) >= course.get("capacity", 0):
        decision = "WAITLIST_ALLOWED"
        violations.append(RuleViolation(code="CAPACITY_FULL", message="课程已满，可加入候补"))
    return EligibilitySnapshot(eligible=not violations, decision=decision, violations=violations, checked_at=_now())


class RecommendationService:
    def __init__(
        self,
        store: InMemoryStore,
        deepseek: DeepSeekAdapter | None = None,
        snapshot_service: CourseSnapshotService = SNAPSHOT_SERVICE,
        rag: LocalCourseRAG | None = None,
    ) -> None:
        self.store = store
        self.deepseek = deepseek or DeepSeekAdapter()
        self.snapshot_service = snapshot_service
        self.rag = rag or DEFAULT_RAG

    async def create(self, student_id: str, payload: RecommendationRequest) -> RecommendationSession:
        snapshot = await self.snapshot_service.refresh(student_id, self.store)
        use_rag = bool(getattr(payload, "use_rag", False))
        rag_status = "NOT_REQUESTED"
        rag_message: str | None = None
        prompt_snapshot = snapshot
        rag_context: str | None = None
        if use_rag:
            try:
                rag_result = await self.rag.retrieve(payload, snapshot)
                course_by_id = {course["id"]: course for course in snapshot["catalog"]}
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
                generated_items = await self.deepseek.recommend(payload, prompt_snapshot, retrieved_context=rag_context)
                model_name = "deepseek_rag"
            else:
                generated_items = await self.deepseek.recommend(payload, snapshot)
                model_name = "deepseek"
            status = "COMPLETED"
        except DeepSeekUnavailable:
            generated_items = fallback_recommendations(payload, snapshot["catalog"])
            status = "FALLBACK"
            model_name = "rule_fallback"
            if use_rag and rag_status == "USED":
                rag_status = "UNAVAILABLE"
                rag_message = "RAG_LLM_UNAVAILABLE"
        course_by_id = {course["id"]: course for course in snapshot["catalog"]}
        items = []
        for rank, generated in enumerate(generated_items, start=1):
            course = course_by_id.get(generated.course_id)
            if course is None:
                continue
            items.append(
                RecommendationItem(
                    course_id=generated.course_id,
                    rank=rank,
                    reasons=[text.strip() for text in generated.reasons],
                    uncertainties=[text.strip() for text in generated.uncertainties],
                    eligibility=current_snapshot_eligibility(student_id, course, snapshot, self.store),
                )
            )
        session = RecommendationSession(
            id=f"rec-{uuid4().hex[:8]}",
            status=status,
            model=model_name,
            rag_status=rag_status,
            rag_message=rag_message,
            items=items,
        )
        self.store.recommendations[session.id] = {"student_id": student_id, **session.model_dump()}
        return session

    def get(self, student_id: str, session_id: str) -> RecommendationSession | None:
        session = self.store.recommendations.get(session_id)
        if not session or session.get("student_id") != student_id:
            return None
        return RecommendationSession(**{key: value for key, value in session.items() if key != "student_id"})
