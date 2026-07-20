from fastapi import APIRouter, Depends, Header, HTTPException

from ..auth import require_role
from ..contracts import (
    EnrollmentRequestIn,
    EnrollmentStatus,
    RecommendationRequest,
    RecommendationSession,
    Role,
    WaitlistStatus,
)
from ..store import STORE, utc_now
from ..storage import get_optional_db
from ..services.course_snapshot import SNAPSHOT_SERVICE
from ..services.recommendation import RecommendationService
from .courses import to_summary

router = APIRouter(prefix="/api/v1/students/me", tags=["student"])


def audit(user: dict, action: str, resource_type: str, resource_id: str, reason: str = "baseline") -> None:
    STORE.audits.append(
        {
            "actor_id": user["id"],
            "subject_student_id": user["id"],
            "actor_role": user["role"],
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "reason": reason,
            "created_at": utc_now(),
        }
    )


@router.post("/recommendations", response_model=None)
async def create_recommendation(
    payload: RecommendationRequest,
    user: dict = Depends(require_role(Role.STUDENT)),
    db=Depends(get_optional_db),
) -> RecommendationSession:
    if db is not None:
        from ..services.database_store import create_recommendation as create_db_recommendation

        session = RecommendationSession(**(await create_db_recommendation(db, user["id"], payload)))
        return {"data": session.model_dump(mode="json"), "meta": {"request_id": "recommendation"}}
    session = await RecommendationService(STORE).create(user["id"], payload)
    audit(user, "RECOMMENDATION_CREATED", "recommendation_session", session.id)
    return {"data": session.model_dump(mode="json"), "meta": {"request_id": "recommendation"}}


@router.get("/recommendations/{session_id}", response_model=None)
async def get_recommendation(
    session_id: str,
    user: dict = Depends(require_role(Role.STUDENT)),
    db=Depends(get_optional_db),
) -> RecommendationSession:
    if db is not None:
        from ..services.database_store import get_recommendation as get_db_recommendation

        result = await get_db_recommendation(db, user["id"], session_id)
        if result is None:
            raise HTTPException(status_code=404, detail="推荐会话不存在")
        session = RecommendationSession(**result)
        return {"data": session.model_dump(mode="json"), "meta": {"request_id": "recommendation"}}
    session = RecommendationService(STORE).get(user["id"], session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="推荐会话不存在")
    return {"data": session.model_dump(mode="json"), "meta": {"request_id": "recommendation"}}


@router.post("/enrollment-requests")
async def enrollment_request(
    payload: EnrollmentRequestIn,
    user: dict = Depends(require_role(Role.STUDENT)),
    db=Depends(get_optional_db),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
) -> dict:
    if db is not None:
        from ..services.database_store import process_enrollment_request

        try:
            result = await process_enrollment_request(
                db,
                student_id=user["id"],
                course_id=payload.course_id,
                request_type=payload.type,
                idempotency_key=idempotency_key,
                request_id=f"student:{user['id']}:{payload.course_id}",
            )
        except ValueError as exc:
            code = str(exc).split(":", 1)[0]
            if code == "COURSE_NOT_FOUND":
                raise HTTPException(status_code=404, detail="课程不存在") from exc
            if code == "NO_RECORD_TO_DROP":
                raise HTTPException(status_code=404, detail="没有可退选或退出的记录") from exc
            raise HTTPException(status_code=422, detail=code) from exc
        if result.get("status") == "REJECTED":
            raise HTTPException(status_code=422, detail=result.get("rule_result", {}))
        return {"data": result, "meta": {"request_id": "enrollment-request"}}
    course = STORE.courses.get(payload.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    key = (user["id"], payload.course_id)

    if payload.type == "DROP":
        if key in STORE.enrollments:
            STORE.enrollments[key]["status"] = EnrollmentStatus.DROPPED.value
            audit(user, "ENROLLMENT_DROPPED", "enrollment", payload.course_id)
            return {"data": {"course_id": payload.course_id, "status": "DROPPED"}}
        if key in STORE.waitlists:
            STORE.waitlists[key]["status"] = WaitlistStatus.REMOVED.value
            audit(user, "WAITLIST_REMOVED", "waitlist", payload.course_id)
            return {"data": {"course_id": payload.course_id, "status": "REMOVED"}}
        raise HTTPException(status_code=404, detail="没有可退选或退出的记录")

    if course["status"] != "OPEN":
        raise HTTPException(status_code=422, detail="课程当前不可选")
    if key in STORE.enrollments and STORE.enrollments[key]["status"] in {"ENROLLED", "CONFLICT_REVIEW"}:
        raise HTTPException(status_code=422, detail="已经选过该课程")

    enrolled_count = sum(
        1
        for record in STORE.enrollments.values()
        if record["course_id"] == course["id"] and record["status"] in {"ENROLLED", "CONFLICT_REVIEW"}
    )
    if payload.type == "ENROLL" and enrolled_count < course["capacity"]:
        STORE.enrollments[key] = {
            "student_id": user["id"],
            "course_id": course["id"],
            "status": EnrollmentStatus.ENROLLED.value,
            "created_at": utc_now(),
        }
        audit(user, "ENROLLMENT_CREATED", "enrollment", course["id"])
        return {"data": {"course_id": course["id"], "status": "ENROLLED"}}

    if payload.type == "WAITLIST":
        waiting = [item for item in STORE.waitlists.values() if item["course_id"] == course["id"] and item["status"] == "WAITING"]
        STORE.waitlists[key] = {
            "student_id": user["id"],
            "course_id": course["id"],
            "status": WaitlistStatus.WAITING.value,
            "position": len(waiting) + 1,
            "joined_at": utc_now(),
        }
        audit(user, "WAITLIST_JOINED", "waitlist", course["id"])
        return {"data": {"course_id": course["id"], "status": "WAITING", "position": len(waiting) + 1}}

    raise HTTPException(status_code=422, detail="CAPACITY_FULL")


@router.get("/enrollments")
async def list_enrollments(user: dict = Depends(require_role(Role.STUDENT)), db=Depends(get_optional_db)) -> dict:
    if db is not None:
        from ..services.database_store import list_student_enrollments

        return {"data": await list_student_enrollments(db, user["id"]), "meta": {"request_id": "enrollments"}}
    records = [record for (student_id, _), record in STORE.enrollments.items() if student_id == user["id"]]
    return {"data": records}


@router.get("/waitlists")
async def list_waitlists(user: dict = Depends(require_role(Role.STUDENT)), db=Depends(get_optional_db)) -> dict:
    if db is not None:
        from ..services.database_store import list_student_waitlists

        return {"data": await list_student_waitlists(db, user["id"]), "meta": {"request_id": "waitlists"}}
    records = [record for (student_id, _), record in STORE.waitlists.items() if student_id == user["id"]]
    return {"data": records}


@router.get("/schedule")
async def get_schedule(user: dict = Depends(require_role(Role.STUDENT)), db=Depends(get_optional_db)) -> dict:
    if db is not None:
        from ..services.database_store import list_student_schedule

        return {"data": await list_student_schedule(db, user["id"]), "meta": {"request_id": "schedule"}}
    snapshot = await SNAPSHOT_SERVICE.refresh(user["id"], STORE)
    return {
        "data": {
            "courses": snapshot["selected_courses"],
            "generated_at": snapshot["generated_at"],
            "cache_backend": SNAPSHOT_SERVICE.cache.backend,
        },
        "meta": {"request_id": "schedule"},
    }


@router.delete("/waitlists/{course_id}")
async def exit_waitlist(
    course_id: str,
    user: dict = Depends(require_role(Role.STUDENT)),
    db=Depends(get_optional_db),
) -> dict:
    if db is not None:
        from sqlalchemy import select
        from ..models import WaitlistEntry

        entry = (
            await db.execute(
                select(WaitlistEntry).where(
                    WaitlistEntry.student_id == user["id"],
                    WaitlistEntry.course_id == course_id,
                    WaitlistEntry.status == "WAITING",
                ).with_for_update()
            )
        ).scalar_one_or_none()
        if entry is None:
            raise HTTPException(status_code=404, detail="未在该课程候补名单中")
        entry.status = "REMOVED"
        await db.flush()
        return {"data": {"status": "REMOVED", "waitlist_id": entry.id}, "meta": {"request_id": "waitlist-exit"}}
    key = (user["id"], course_id)
    if key not in STORE.waitlists or STORE.waitlists[key].get("status") != "WAITING":
        raise HTTPException(status_code=404, detail="未在该课程候补名单中")
    STORE.waitlists[key]["status"] = "REMOVED"
    return {"data": {"status": "REMOVED", "course_id": course_id}}


@router.get("/audit-logs")
async def list_audits(user: dict = Depends(require_role(Role.STUDENT)), db=Depends(get_optional_db)) -> dict:
    if db is not None:
        from ..services.database_store import list_student_audits

        return {"data": await list_student_audits(db, user["id"]), "meta": {"request_id": "audit-logs"}}
    records = [record for record in STORE.audits if record["subject_student_id"] == user["id"]]
    return {"data": records}
