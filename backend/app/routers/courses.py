from fastapi import APIRouter, Depends, HTTPException, Query

from ..auth import get_current_user
from ..contracts import CourseSummary
from ..store import STORE
from ..storage import get_optional_db

router = APIRouter(prefix="/api/v1/courses", tags=["courses"])


def to_summary(course: dict) -> CourseSummary:
    enrolled_count = sum(
        1
        for record in STORE.enrollments.values()
        if record["course_id"] == course["id"] and record["status"] in {"ENROLLED", "CONFLICT_REVIEW"}
    )
    waitlist_count = sum(
        1
        for record in STORE.waitlists.values()
        if record["course_id"] == course["id"] and record["status"] == "WAITING"
    )
    return CourseSummary(
        **course,
        enrolled_count=enrolled_count,
        waitlist_count=waitlist_count,
    )


@router.get("", response_model=None)
async def list_courses(
    keyword: str | None = Query(default=None),
    status: str | None = Query(default=None),
    _: dict = Depends(get_current_user),
    db=Depends(get_optional_db),
) -> list[CourseSummary] | dict:
    if db is not None:
        from ..services.database_store import list_course_summaries

        return {"data": await list_course_summaries(db, keyword=keyword, status=status), "meta": {"request_id": "courses"}}
    return [to_summary(course) for course in STORE.courses.values()]


@router.get("/{course_id}", response_model=None)
async def get_course(course_id: str, _: dict = Depends(get_current_user), db=Depends(get_optional_db)) -> CourseSummary | dict:
    if db is not None:
        from ..services.database_store import _course, course_summary

        course = await _course(db, course_id)
        if course is None:
            raise HTTPException(status_code=404, detail="课程不存在")
        return {"data": await course_summary(db, course), "meta": {"request_id": "course"}}
    course = STORE.courses.get(course_id)
    if not course:
        raise HTTPException(status_code=404, detail="课程不存在")
    return to_summary(course)
