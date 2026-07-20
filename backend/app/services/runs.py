from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Callable
from uuid import uuid4

from ..schemas.admin import (
    AdminErrorCode,
    ErrorBody,
    RecalculationRun,
    RecalculationSummary,
    RecalculationResult,
    RunStatus,
    TriggerType,
)


class RunRegistryError(RuntimeError):
    """Base error for the replaceable in-memory run adapter."""


class RunAlreadyActiveError(RunRegistryError):
    def __init__(self, run: RecalculationRun):
        self.run = run
        super().__init__(f"course {run.course_id} already has active run {run.id}")


class RunNotFoundError(RunRegistryError):
    pass


class InvalidRunTransitionError(RunRegistryError):
    pass


class RunRegistry:
    """Small, concurrency-safe run registry used until A provides persistence."""

    _TRANSITIONS = {
        RunStatus.PENDING: {RunStatus.RUNNING, RunStatus.FAILED},
        RunStatus.RUNNING: {RunStatus.SUCCEEDED, RunStatus.FAILED},
        RunStatus.SUCCEEDED: set(),
        RunStatus.FAILED: set(),
    }

    def __init__(
        self,
        id_factory: Callable[[], str] | None = None,
        on_change: Callable[[RecalculationRun], None] | None = None,
    ) -> None:
        self._runs: dict[str, RecalculationRun] = {}
        self._active_by_course: dict[str, str] = {}
        self._idempotency: dict[tuple[str, str, str], str] = {}
        self._lock = asyncio.Lock()
        self._id_factory = id_factory or (lambda: f"run-{uuid4().hex[:12]}")
        self._on_change = on_change

    def _notify(self, run: RecalculationRun) -> None:
        """Mirror lifecycle changes into the replaceable persistence adapter."""

        if self._on_change is not None:
            self._on_change(run)

    async def start(
        self,
        *,
        course_id: str,
        trigger_type: TriggerType,
        operator_id: str,
        idempotency_key: str | None = None,
    ) -> tuple[RecalculationRun, bool]:
        """Create a PENDING run or return the first result for the same idempotency key."""

        async with self._lock:
            idempotency_ref = (operator_id, course_id, idempotency_key) if idempotency_key else None
            if idempotency_ref and idempotency_ref in self._idempotency:
                return self._runs[self._idempotency[idempotency_ref]], True

            active_id = self._active_by_course.get(course_id)
            if active_id:
                active = self._runs[active_id]
                if active.status in {RunStatus.PENDING, RunStatus.RUNNING}:
                    raise RunAlreadyActiveError(active)
                del self._active_by_course[course_id]

            run = RecalculationRun(
                id=self._id_factory(),
                course_id=course_id,
                trigger_type=trigger_type,
                operator_id=operator_id,
                status=RunStatus.PENDING,
                summary=RecalculationSummary(),
            )
            self._runs[run.id] = run
            self._active_by_course[course_id] = run.id
            if idempotency_ref:
                self._idempotency[idempotency_ref] = run.id
            self._notify(run)
            return run, False

    async def get(self, run_id: str) -> RecalculationRun:
        async with self._lock:
            try:
                return self._runs[run_id]
            except KeyError as exc:
                raise RunNotFoundError(run_id) from exc

    async def transition(
        self,
        run_id: str,
        status: RunStatus,
        *,
        summary: RecalculationSummary | dict[str, Any] | None = None,
        results: list[RecalculationResult | dict[str, Any]] | None = None,
        error: ErrorBody | dict[str, Any] | None = None,
    ) -> RecalculationRun:
        async with self._lock:
            current = self._runs.get(run_id)
            if current is None:
                raise RunNotFoundError(run_id)
            if status not in self._TRANSITIONS[current.status]:
                raise InvalidRunTransitionError(f"{current.status.value} -> {status.value}")

            patch: dict[str, Any] = {"status": status}
            if summary is not None:
                patch["summary"] = summary
            if results is not None:
                patch["results"] = results
            if error is not None:
                patch["error"] = error
            if status == RunStatus.RUNNING:
                patch["started_at"] = datetime.now(timezone.utc)
            if status in {RunStatus.SUCCEEDED, RunStatus.FAILED}:
                patch["finished_at"] = datetime.now(timezone.utc)

            updated = RecalculationRun.model_validate(current.model_dump(mode="python") | patch)
            self._runs[run_id] = updated
            if status in {RunStatus.SUCCEEDED, RunStatus.FAILED}:
                self._active_by_course.pop(updated.course_id, None)
            self._notify(updated)
            return updated

    async def fail(self, run_id: str, message: str, *, details: list[dict[str, Any]] | None = None) -> RecalculationRun:
        return await self.transition(
            run_id,
            RunStatus.FAILED,
            error=ErrorBody(
                code=AdminErrorCode.RECALCULATION_FAILED.value,
                message=message,
                details=details or [],
            ),
        )
