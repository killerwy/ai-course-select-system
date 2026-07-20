from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, Header, Query, Request
from fastapi.responses import JSONResponse

from ..auth import require_role
from ..contracts import ApprovalDecision, CancelRequest, CourseChangePreviewRequest, CourseSummary, CourseStatus, CourseWriteRequest, ExpandRequest, RescheduleRequest, Role
from ..schemas.admin import (
    AdminCourseFilters,
    AdminErrorCode,
    ApprovalFilters,
    ApprovalStatus,
    AuditFilters,
    AuditRecord,
    RecalculationRun,
    RunStatus,
    TriggerType,
    error_response,
    success_response,
)
from ..services.approval import ApprovalService
from ..services.audit import build_audit_record
from ..services.audit_query import query_admin_audits
from ..services.course_admin import CourseMutationService
from ..services.course_change_preview import CourseChangePreviewService
from ..services.course_operation import CourseOperationApprovalService, decorate_courses_with_pending
from ..services.recalculation import RecalculationService
from ..services.runs import RunAlreadyActiveError, RunNotFoundError, RunRegistry
from ..services.store_adapter import BaselineRuleChecker, StoreAdminRepository, StoreAuditWriter
from ..tasks.recalculation import RecalculationTaskRunner, enqueue_recalculation
from ..store import STORE
from ..storage import get_optional_db
from .courses import to_summary

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])


def _sync_run(run: RecalculationRun) -> None:
    STORE.runs[run.id] = run.model_dump(mode="json")


REPOSITORY = StoreAdminRepository()
AUDIT_WRITER = StoreAuditWriter()
RUN_REGISTRY = RunRegistry(on_change=_sync_run)
RULE_CHECKER = BaselineRuleChecker(REPOSITORY)
MUTATION_SERVICE = CourseMutationService(repository=REPOSITORY, run_registry=RUN_REGISTRY, audit_writer=AUDIT_WRITER)
RECALCULATION_SERVICE = RecalculationService(
    repository=REPOSITORY,
    rule_checker=RULE_CHECKER,
    audit_writer=AUDIT_WRITER,
    run_registry=RUN_REGISTRY,
)
TASK_RUNNER = RecalculationTaskRunner(RECALCULATION_SERVICE, RUN_REGISTRY)
APPROVAL_SERVICE = ApprovalService(repository=REPOSITORY, rule_checker=RULE_CHECKER, audit_writer=AUDIT_WRITER)
COURSE_OPERATION_SERVICE = CourseOperationApprovalService(repository=REPOSITORY, mutation_service=MUTATION_SERVICE, audit_writer=AUDIT_WRITER)
COURSE_CHANGE_PREVIEW_SERVICE = CourseChangePreviewService(REPOSITORY)


def _request_id(request: Request) -> str:
    return request.headers.get("X-Request-ID") or f"req-{uuid4().hex[:12]}"


def _dump(value):
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {key: _dump(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_dump(item) for item in value]
    return value


def _error_status(code: str) -> int:
    if code in {"COURSE_NOT_FOUND", "RUN_NOT_FOUND", "APPROVAL_NOT_FOUND", "COURSE_OPERATION_NOT_FOUND"}:
        return 404
    if code in {"RUN_ALREADY_ACTIVE", "CONCURRENT_MODIFICATION", "COURSE_CANCELLED", "COURSE_ALREADY_CANCELLED", "APPROVAL_RECHECK_FAILED", "APPROVAL_NOT_PENDING", "COURSE_ALREADY_EXISTS", "COURSE_OPERATION_NOT_PENDING", "COURSE_OPERATION_PENDING"}:
        return 409
    if code in {"INVALID_CAPACITY_DELTA", "INVALID_SCHEDULE", "EMPTY_REASON", "EMPTY_COMMENT", "APPROVAL_RULE_NOT_ALLOWED", "INVALID_TIME_RANGE", "INVALID_FILTER", "INVALID_COURSE", "PREREQUISITE_NOT_FOUND", "INVALID_IDEMPOTENCY_KEY", "INVALID_COURSE_OPERATION"}:
        return 422
    return 500


def _failure(request: Request, exc: Exception, default_code: str) -> JSONResponse:
    if isinstance(exc, KeyError):
        code = default_code
        message = "resource not found"
    elif isinstance(exc, RunAlreadyActiveError):
        code = AdminErrorCode.RUN_ALREADY_ACTIVE.value
        message = str(exc)
    elif isinstance(exc, RunNotFoundError):
        code = AdminErrorCode.RUN_NOT_FOUND.value
        message = "recalculation run not found"
    else:
        candidate = str(exc).strip()
        code = candidate if candidate and candidate.replace("_", "").isalnum() and candidate.upper() == candidate else default_code
        message = candidate or default_code
    return JSONResponse(status_code=_error_status(code), content=error_response(code, message, _request_id(request)))


def _course_data(course: dict) -> dict:
    data = to_summary(course).model_dump(mode="json")
    if course.get("pending_operation"):
        data["pending_operation"] = _dump(course["pending_operation"])
    return data


def _start_idempotency(request: Request, header_value: str | None) -> str | None:
    value = header_value or request.headers.get("Idempotency-Key")
    if value and len(value) > 64:
        raise ValueError("INVALID_IDEMPOTENCY_KEY")
    return value


async def _enqueue_if_needed(background_tasks: BackgroundTasks, run: RecalculationRun, reused: bool) -> None:
    if not reused and run.status == RunStatus.PENDING:
        enqueue_recalculation(background_tasks, TASK_RUNNER, run.id)


@router.post("/courses", response_model=None)
async def create_course(
    request: Request,
    payload: CourseWriteRequest,
    user: dict = Depends(require_role(Role.ACADEMIC)),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db=Depends(get_optional_db),
) -> dict | JSONResponse:
    try:
        if db is not None and hasattr(db, "execute"):
            from ..services.database_admin import DatabaseAdminService

            result = await DatabaseAdminService(db).submit_course_operation(
                operation="CREATE",
                course_id=None,
                payload={
                    "code": payload.code,
                    "name": payload.name,
                    "teacher_name": payload.teacher_name,
                    "credits": payload.credits,
                    "capacity": payload.capacity,
                    "schedules": [item.model_dump() for item in payload.schedules],
                    "prerequisites": payload.prerequisites,
                },
                requester_id=user["id"],
                request_id=_request_id(request),
                idempotency_key=_start_idempotency(request, idempotency_key),
            )
            return success_response(
                {
                    "course": None,
                    "operation": result["operation"],
                    "run": None,
                    "reused": result["reused"],
                },
                _request_id(request),
            )
        result = await COURSE_OPERATION_SERVICE.submit(
            operation="CREATE",
            course_id=None,
            payload={
                "code": payload.code,
                "name": payload.name,
                "teacher_name": payload.teacher_name,
                "credits": payload.credits,
                "capacity": payload.capacity,
                "schedules": [item.model_dump() for item in payload.schedules],
                "prerequisites": payload.prerequisites,
            },
            requester_id=user["id"],
            idempotency_key=_start_idempotency(request, idempotency_key),
        )
        return success_response({"course": None, "operation": result["operation"], "run": None, "reused": result["reused"]}, _request_id(request))
    except Exception as exc:
        return _failure(request, exc, AdminErrorCode.COURSE_ALREADY_EXISTS.value)


@router.patch("/courses/{course_id}", response_model=None)
async def update_course_details(
    request: Request,
    course_id: str,
    payload: CourseWriteRequest,
    background_tasks: BackgroundTasks,
    expected_version: int | None = Query(default=None, ge=0),
    user: dict = Depends(require_role(Role.ACADEMIC)),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db=Depends(get_optional_db),
) -> dict | JSONResponse:
    try:
        if db is not None and hasattr(db, "execute"):
            from ..services.database_admin import DatabaseAdminService

            result = await DatabaseAdminService(db).submit_course_operation(
                operation="UPDATE",
                course_id=course_id,
                payload={
                    "code": payload.code,
                    "name": payload.name,
                    "teacher_name": payload.teacher_name,
                    "credits": payload.credits,
                    "capacity": payload.capacity,
                    "schedules": [item.model_dump() for item in payload.schedules],
                    "prerequisites": payload.prerequisites,
                    "expected_version": expected_version,
                },
                requester_id=user["id"],
                request_id=_request_id(request),
                idempotency_key=_start_idempotency(request, idempotency_key),
            )
            return success_response({"course": None, "operation": result["operation"], "run": None, "reused": result["reused"]}, _request_id(request))
        result = await COURSE_OPERATION_SERVICE.submit(
            operation="UPDATE",
            course_id=course_id,
            payload={
                "code": payload.code,
                "name": payload.name,
                "teacher_name": payload.teacher_name,
                "credits": payload.credits,
                "capacity": payload.capacity,
                "schedules": [item.model_dump() for item in payload.schedules],
                "prerequisites": payload.prerequisites,
                "expected_version": expected_version,
            },
            requester_id=user["id"],
            idempotency_key=_start_idempotency(request, idempotency_key),
        )
        return success_response({"course": None, "operation": result["operation"], "run": None, "reused": result["reused"]}, _request_id(request))
    except Exception as exc:
        return _failure(request, exc, AdminErrorCode.COURSE_NOT_FOUND.value)


@router.get("/courses")
async def list_admin_courses(
    request: Request,
    status: CourseStatus | None = Query(default=None),
    keyword: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: dict = Depends(require_role(Role.ACADEMIC)),
    db=Depends(get_optional_db),
) -> dict:
    if db is not None and hasattr(db, "execute"):
        from ..services.database_admin import DatabaseAdminService

        values = await DatabaseAdminService(db).list_courses(status=status.value if status else None, keyword=keyword)
        total = len(values)
        start = (page - 1) * page_size
        return success_response(values[start : start + page_size], _request_id(request), page=page, page_size=page_size, total=total)
    filters = AdminCourseFilters(status=status, keyword=keyword, page=page, page_size=page_size)
    courses = []
    for course in STORE.courses.values():
        if filters.keyword and filters.keyword.lower() not in f"{course.get('code', '')} {course.get('name', '')}".lower():
            continue
        courses.append(_course_data(course))
    courses = decorate_courses_with_pending(courses, await COURSE_OPERATION_SERVICE.list(status="PENDING"))
    if filters.keyword:
        needle = filters.keyword.casefold()
        courses = [course for course in courses if needle in f"{course.get('code', '')} {course.get('name', '')}".casefold()]
    if filters.status:
        courses = [course for course in courses if course.get("status") == filters.status.value]
    total = len(courses)
    start = (filters.page - 1) * filters.page_size
    return success_response(courses[start : start + filters.page_size], _request_id(request), page=filters.page, page_size=filters.page_size, total=total)


@router.post("/courses/{course_id}/change-preview", response_model=None)
async def preview_course_change(
    request: Request,
    course_id: str,
    payload: CourseChangePreviewRequest,
    _: dict = Depends(require_role(Role.ACADEMIC)),
    db=Depends(get_optional_db),
) -> dict | JSONResponse:
    try:
        schedules = [item.model_dump() for item in payload.schedules] if payload.schedules is not None else None
        if db is not None and hasattr(db, "execute"):
            from ..services.database_admin import DatabaseAdminService

            result = await DatabaseAdminService(db).preview_course_change(
                course_id=course_id,
                operation=payload.operation,
                capacity=payload.capacity,
                schedules=schedules,
            )
        else:
            result = await COURSE_CHANGE_PREVIEW_SERVICE.preview(
                course_id=course_id,
                operation=payload.operation,
                capacity=payload.capacity,
                schedules=schedules,
            )
        return success_response(result, _request_id(request))
    except Exception as exc:
        return _failure(request, exc, AdminErrorCode.COURSE_NOT_FOUND.value)


@router.post("/courses/{course_id}/expand", response_model=None)
async def expand_course(
    request: Request,
    background_tasks: BackgroundTasks,
    course_id: str,
    payload: ExpandRequest,
    expected_version: int | None = Query(default=None, ge=0),
    user: dict = Depends(require_role(Role.ACADEMIC)),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db=Depends(get_optional_db),
) -> dict | JSONResponse:
    try:
        if db is not None and hasattr(db, "execute"):
            from ..services.database_admin import DatabaseAdminService

            result = await DatabaseAdminService(db).mutate_course(
                course_id=course_id, operation="EXPAND", operator_id=user["id"], request_id=_request_id(request),
                idempotency_key=_start_idempotency(request, idempotency_key), expected_version=expected_version,
                capacity_delta=payload.capacity_delta,
            )
            return success_response(result, _request_id(request))
        result = await MUTATION_SERVICE.expand(course_id=course_id, capacity_delta=payload.capacity_delta, operator_id=user["id"], idempotency_key=_start_idempotency(request, idempotency_key), expected_version=expected_version)
        await _enqueue_if_needed(background_tasks, result["run"], result["reused"])
        return success_response({"course": _course_data(result["course"]), "run": _dump(result["run"]), "reused": result["reused"]}, _request_id(request))
    except Exception as exc:
        return _failure(request, exc, AdminErrorCode.COURSE_NOT_FOUND.value)


@router.post("/courses/{course_id}/reschedule", response_model=None)
async def reschedule_course(
    request: Request,
    background_tasks: BackgroundTasks,
    course_id: str,
    payload: RescheduleRequest,
    expected_version: int | None = Query(default=None, ge=0),
    user: dict = Depends(require_role(Role.ACADEMIC)),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db=Depends(get_optional_db),
) -> dict | JSONResponse:
    try:
        if db is not None and hasattr(db, "execute"):
            from ..services.database_admin import DatabaseAdminService

            result = await DatabaseAdminService(db).mutate_course(
                course_id=course_id, operation="RESCHEDULE", operator_id=user["id"], request_id=_request_id(request),
                idempotency_key=_start_idempotency(request, idempotency_key), expected_version=expected_version,
                schedules=[item.model_dump() for item in payload.schedules],
            )
            return success_response(result, _request_id(request))
        result = await MUTATION_SERVICE.reschedule(course_id=course_id, schedules=payload.schedules, operator_id=user["id"], idempotency_key=_start_idempotency(request, idempotency_key), expected_version=expected_version)
        await _enqueue_if_needed(background_tasks, result["run"], result["reused"])
        return success_response({"course": _course_data(result["course"]), "run": _dump(result["run"]), "reused": result["reused"]}, _request_id(request))
    except Exception as exc:
        return _failure(request, exc, AdminErrorCode.COURSE_NOT_FOUND.value)


@router.post("/courses/{course_id}/cancel", response_model=None)
async def cancel_course(
    request: Request,
    course_id: str,
    payload: CancelRequest,
    expected_version: int | None = Query(default=None, ge=0),
    user: dict = Depends(require_role(Role.ACADEMIC)),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db=Depends(get_optional_db),
) -> dict | JSONResponse:
    try:
        if db is not None and hasattr(db, "execute"):
            from ..services.database_admin import DatabaseAdminService

            result = await DatabaseAdminService(db).submit_course_operation(
                operation="CANCEL",
                course_id=course_id,
                payload={"reason": payload.reason, "expected_version": expected_version},
                requester_id=user["id"],
                request_id=_request_id(request),
                idempotency_key=_start_idempotency(request, idempotency_key),
            )
            return success_response({"course": None, "operation": result["operation"], "run": None, "reused": result["reused"]}, _request_id(request))
        result = await COURSE_OPERATION_SERVICE.submit(
            operation="CANCEL",
            course_id=course_id,
            payload={"reason": payload.reason, "expected_version": expected_version},
            requester_id=user["id"],
            idempotency_key=_start_idempotency(request, idempotency_key),
        )
        return success_response({"course": None, "operation": result["operation"], "run": None, "reused": result["reused"]}, _request_id(request))
    except Exception as exc:
        return _failure(request, exc, AdminErrorCode.COURSE_NOT_FOUND.value)


@router.post("/courses/{course_id}/recalculate", response_model=None)
async def recalculate_course(
    request: Request,
    background_tasks: BackgroundTasks,
    course_id: str,
    expected_version: int | None = Query(default=None, ge=0),
    user: dict = Depends(require_role(Role.ACADEMIC)),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db=Depends(get_optional_db),
) -> dict | JSONResponse:
    try:
        if db is not None and hasattr(db, "execute"):
            from ..services.database_admin import DatabaseAdminService

            result = await DatabaseAdminService(db).recalculate(
                course_id=course_id, operator_id=user["id"], request_id=_request_id(request),
                idempotency_key=_start_idempotency(request, idempotency_key), expected_version=expected_version,
            )
            return success_response(result["run"], _request_id(request))
        course = await REPOSITORY.get_course(course_id)
        if expected_version is not None and course.get("version", 0) != expected_version:
            raise ValueError("CONCURRENT_MODIFICATION")
        run, reused = await RUN_REGISTRY.start(course_id=course_id, trigger_type=TriggerType.MANUAL, operator_id=user["id"], idempotency_key=_start_idempotency(request, idempotency_key))
        await AUDIT_WRITER.append(build_audit_record(actor_id=user["id"], actor_role=Role.ACADEMIC, action="RECALCULATION_STARTED", resource_type="recalculation_run", resource_id=run.id, run_id=run.id, request_id=_request_id(request)))
        await _enqueue_if_needed(background_tasks, run, reused)
        return success_response(_dump(run), _request_id(request))
    except Exception as exc:
        return _failure(request, exc, AdminErrorCode.COURSE_NOT_FOUND.value)


@router.get("/recalculation-runs", response_model=None)
async def list_runs(
    request: Request,
    _: dict = Depends(require_role(Role.ACADEMIC)),
    db=Depends(get_optional_db),
) -> dict | JSONResponse:
    try:
        if db is not None and hasattr(db, "execute"):
            from ..services.database_admin import DatabaseAdminService
            from ..models import RecalculationRun as RunModel
            from sqlalchemy import select

            runs = list(
                (await db.execute(
                    select(RunModel).order_by(RunModel.created_at.desc(), RunModel.id.desc())
                )).scalars().all()
            )
            result = [
                {
                    "id": run.id,
                    "trigger_type": run.trigger_type,
                    "course_id": run.course_id,
                    "operator_id": run.operator_id,
                    "status": run.status,
                    "created_at": run.created_at.isoformat() if run.created_at else None,
                    "finished_at": run.finished_at.isoformat() if run.finished_at else None,
                }
                for run in runs
            ]
            return success_response(result, _request_id(request))
        runs = [_dump(run) for run in STORE.runs.values()]
        return success_response(runs, _request_id(request))
    except Exception as exc:
        return _failure(request, exc, AdminErrorCode.INVALID_FILTER.value)


@router.get("/recalculation-runs/{run_id}", response_model=None)
async def get_run(request: Request, run_id: str, _: dict = Depends(require_role(Role.ACADEMIC)), db=Depends(get_optional_db)) -> dict | JSONResponse:
    try:
        if db is not None and hasattr(db, "execute"):
            from ..services.database_admin import DatabaseAdminService

            return success_response(await DatabaseAdminService(db).get_run(run_id), _request_id(request))
        return success_response(_dump(await RUN_REGISTRY.get(run_id)), _request_id(request))
    except RunNotFoundError:
        stored = STORE.runs.get(run_id)
        if stored is not None:
            return success_response(stored, _request_id(request))
        return _failure(request, RunNotFoundError(run_id), AdminErrorCode.RUN_NOT_FOUND.value)


@router.get("/exception-approvals", response_model=None)
async def list_approvals(
    request: Request,
    status: ApprovalStatus | None = Query(default=None),
    course_id: str | None = Query(default=None),
    student_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: dict = Depends(require_role(Role.ACADEMIC)),
    db=Depends(get_optional_db),
) -> dict | JSONResponse:
    try:
        if db is not None and hasattr(db, "execute"):
            from ..services.database_admin import DatabaseAdminService

            values = await DatabaseAdminService(db).list_approvals(status=status.value if status else None, course_id=course_id, student_id=student_id)
            total = len(values)
            start = (page - 1) * page_size
            return success_response(values[start : start + page_size], _request_id(request), page=page, page_size=page_size, total=total)
        filters = ApprovalFilters(status=status, course_id=course_id, student_id=student_id, page=page, page_size=page_size)
        values = await REPOSITORY.list_approvals({"status": status.value if status else None, "course_id": course_id, "student_id": student_id})
        total = len(values)
        start = (filters.page - 1) * filters.page_size
        return success_response([_dump(item) for item in values[start : start + filters.page_size]], _request_id(request), page=filters.page, page_size=filters.page_size, total=total)
    except Exception as exc:
        return _failure(request, exc, AdminErrorCode.INVALID_FILTER.value)


@router.post("/exception-approvals/{approval_id}/approve", response_model=None)
async def approve(request: Request, approval_id: str, payload: ApprovalDecision, user: dict = Depends(require_role(Role.ACADEMIC)), db=Depends(get_optional_db)) -> dict | JSONResponse:
    try:
        if db is not None and hasattr(db, "execute"):
            from ..services.database_admin import DatabaseAdminService

            result = await DatabaseAdminService(db).decide_approval(approval_id=approval_id, decision="APPROVE", comment=payload.comment, waived_rules=payload.waived_rules, reviewer_id=user["id"], request_id=_request_id(request))
            return success_response(result, _request_id(request))
        result = await APPROVAL_SERVICE.approve(approval_id=approval_id, comment=payload.comment, waived_rules=payload.waived_rules, reviewer_id=user["id"])
        return success_response(_dump(result), _request_id(request))
    except Exception as exc:
        return _failure(request, exc, AdminErrorCode.APPROVAL_NOT_FOUND.value)


@router.post("/exception-approvals/{approval_id}/reject", response_model=None)
async def reject(request: Request, approval_id: str, payload: ApprovalDecision, user: dict = Depends(require_role(Role.ACADEMIC)), db=Depends(get_optional_db)) -> dict | JSONResponse:
    try:
        if db is not None and hasattr(db, "execute"):
            from ..services.database_admin import DatabaseAdminService

            result = await DatabaseAdminService(db).decide_approval(approval_id=approval_id, decision="REJECT", comment=payload.comment, waived_rules=[], reviewer_id=user["id"], request_id=_request_id(request))
            return success_response(result, _request_id(request))
        result = await APPROVAL_SERVICE.reject(approval_id=approval_id, comment=payload.comment, reviewer_id=user["id"])
        return success_response(_dump(result), _request_id(request))
    except Exception as exc:
        return _failure(request, exc, AdminErrorCode.APPROVAL_NOT_FOUND.value)


@router.get("/course-operation-approvals", response_model=None)
async def list_course_operation_approvals(
    request: Request,
    status: ApprovalStatus | None = Query(default=None),
    course_id: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: dict = Depends(require_role(Role.ACADEMIC)),
    db=Depends(get_optional_db),
) -> dict | JSONResponse:
    try:
        if db is not None and hasattr(db, "execute"):
            from ..services.database_admin import DatabaseAdminService

            values = await DatabaseAdminService(db).list_course_operations(status=status.value if status else None, course_id=course_id)
        else:
            values = await COURSE_OPERATION_SERVICE.list(status=status.value if status else None, course_id=course_id)
        total = len(values)
        start = (page - 1) * page_size
        return success_response(values[start : start + page_size], _request_id(request), page=page, page_size=page_size, total=total)
    except Exception as exc:
        return _failure(request, exc, AdminErrorCode.INVALID_FILTER.value)


@router.post("/course-operation-approvals/{operation_id}/approve", response_model=None)
async def approve_course_operation(
    request: Request,
    operation_id: str,
    background_tasks: BackgroundTasks,
    payload: ApprovalDecision,
    user: dict = Depends(require_role(Role.ACADEMIC)),
    db=Depends(get_optional_db),
) -> dict | JSONResponse:
    try:
        if db is not None and hasattr(db, "execute"):
            from ..services.database_admin import DatabaseAdminService

            result = await DatabaseAdminService(db).decide_course_operation(operation_id=operation_id, decision="APPROVE", comment=payload.comment, reviewer_id=user["id"], request_id=_request_id(request))
        else:
            result = await COURSE_OPERATION_SERVICE.decide(operation_id=operation_id, decision="APPROVE", comment=payload.comment, reviewer_id=user["id"])
            if result.get("run"):
                await _enqueue_if_needed(background_tasks, result["run"], result.get("reused", False))
        return success_response(_dump(result), _request_id(request))
    except Exception as exc:
        return _failure(request, exc, AdminErrorCode.COURSE_OPERATION_NOT_FOUND.value)


@router.post("/course-operation-approvals/{operation_id}/reject", response_model=None)
async def reject_course_operation(
    request: Request,
    operation_id: str,
    payload: ApprovalDecision,
    user: dict = Depends(require_role(Role.ACADEMIC)),
    db=Depends(get_optional_db),
) -> dict | JSONResponse:
    try:
        if db is not None and hasattr(db, "execute"):
            from ..services.database_admin import DatabaseAdminService

            result = await DatabaseAdminService(db).decide_course_operation(operation_id=operation_id, decision="REJECT", comment=payload.comment, reviewer_id=user["id"], request_id=_request_id(request))
        else:
            result = await COURSE_OPERATION_SERVICE.decide(operation_id=operation_id, decision="REJECT", comment=payload.comment, reviewer_id=user["id"])
        return success_response(_dump(result), _request_id(request))
    except Exception as exc:
        return _failure(request, exc, AdminErrorCode.COURSE_OPERATION_NOT_FOUND.value)


def _coerce_audits() -> list[AuditRecord]:
    values: list[AuditRecord] = []
    for raw in STORE.audits:
        try:
            values.append(AuditRecord.model_validate(raw))
            continue
        except Exception:
            pass
        try:
            created_at = raw.get("created_at")
            when = datetime.fromisoformat(created_at) if isinstance(created_at, str) else datetime.now(timezone.utc)
            values.append(build_audit_record(actor_id=str(raw.get("actor_id", "system")), actor_role=Role(str(raw.get("actor_role", Role.ACADEMIC.value))), action=str(raw.get("action", "UNKNOWN")), resource_type=str(raw.get("resource_type", "unknown")), resource_id=str(raw.get("resource_id", "unknown")), subject_student_id=raw.get("subject_student_id"), reason=raw.get("reason"), request_id=f"legacy:{raw.get('resource_id', 'unknown')}", created_at=when))
        except Exception:
            continue
    return values


@router.get("/audit-logs", response_model=None)
async def list_audits(
    request: Request,
    course_id: str | None = Query(default=None),
    student_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    run_id: str | None = Query(default=None),
    from_: datetime | None = Query(default=None, alias="from"),
    to: datetime | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    _: dict = Depends(require_role(Role.ACADEMIC)),
    db=Depends(get_optional_db),
) -> dict | JSONResponse:
    try:
        if db is not None and hasattr(db, "execute"):
            from ..services.database_admin import DatabaseAdminService

            values, total = await DatabaseAdminService(db).list_audits(course_id=course_id, student_id=student_id, action=action, run_id=run_id, from_=from_, to=to)
            start = (page - 1) * page_size
            return success_response(values[start : start + page_size], _request_id(request), page=page, page_size=page_size, total=total)
        filters = AuditFilters(course_id=course_id, student_id=student_id, action=action, run_id=run_id, **{"from": from_, "to": to, "page": page, "page_size": page_size})
        records, total = query_admin_audits(_coerce_audits(), filters, actor_role=Role.ACADEMIC)
        return success_response([_dump(item) for item in records], _request_id(request), page=page, page_size=page_size, total=total)
    except Exception as exc:
        return _failure(request, exc, AdminErrorCode.INVALID_FILTER.value)
