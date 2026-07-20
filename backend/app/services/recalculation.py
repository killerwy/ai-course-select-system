from __future__ import annotations

import asyncio
from typing import Any

from ..contracts import Role
from ..ports.admin import RuleChecker, stable_waitlist_key
from ..schemas.admin import RecalculationResult, RecalculationSummary, RunStatus
from .audit import build_audit_record
from .runs import RunRegistry


class RecalculationService:
    """Run the shared-rule, sequential waitlist algorithm for one course."""

    def __init__(
        self,
        *,
        repository: Any,
        rule_checker: RuleChecker,
        audit_writer: Any | None,
        run_registry: RunRegistry,
    ) -> None:
        self.repository = repository
        self.rule_checker = rule_checker
        self.audit_writer = audit_writer
        self.run_registry = run_registry
        self._course_locks: dict[str, asyncio.Lock] = {}

    async def execute(self, run_id: str):
        run = await self.run_registry.get(run_id)
        course_lock = self._course_locks.setdefault(run.course_id, asyncio.Lock())
        async with course_lock:
            snapshot = await self.repository.snapshot() if hasattr(self.repository, "snapshot") else None
            try:
                run = await self.run_registry.transition(run_id, RunStatus.RUNNING)
                course = await self.repository.lock_course(run.course_id)
                if course.get("status") == "CANCELLED":
                    raise ValueError("COURSE_CANCELLED")

                enrollments = await self.repository.list_enrollments(run.course_id)
                waiting = sorted(await self.repository.list_waiting(run.course_id), key=stable_waitlist_key)
                occupied = sum(1 for item in enrollments if item.get("status") in {"ENROLLED", "CONFLICT_REVIEW"})
                available = max(int(course.get("capacity", 0)) - occupied, 0)

                results: list[RecalculationResult] = []
                summary = RecalculationSummary()
                for entry in waiting:
                    summary.checked += 1
                    student_id = str(entry["student_id"])
                    entry_id = str(entry["id"])
                    rule_result = await self.rule_checker.check_enrollment(student_id, run.course_id)
                    violation = next((item for item in rule_result.get("violations", []) if item.get("blocking")), None)
                    if not rule_result.get("eligible", False) or violation:
                        reason_code = str((violation or {}).get("code") or rule_result.get("decision") or "RULE_REJECTED")
                        details = {"violations": rule_result.get("violations", []), "decision": rule_result.get("decision")}
                        await self.repository.skip_waitlist(entry_id, reason_code, details)
                        results.append(
                            RecalculationResult(
                                entity_type="WAITLIST",
                                entity_id=entry_id,
                                student_id=student_id,
                                old_status="WAITING",
                                new_status="SKIPPED",
                                reason_code=reason_code,
                                details=details,
                            )
                        )
                        summary.skipped += 1
                        await self._audit_transition(run, entry, "WAITLIST_SKIPPED", "SKIPPED", reason_code)
                        continue

                    if available <= 0:
                        results.append(
                            RecalculationResult(
                                entity_type="WAITLIST",
                                entity_id=entry_id,
                                student_id=student_id,
                                old_status="WAITING",
                                new_status="WAITING",
                                reason_code="CAPACITY_FULL",
                                details={"capacity": course.get("capacity"), "occupied": occupied},
                            )
                        )
                        continue

                    await self.repository.promote_waitlist(entry_id, student_id, run.course_id)
                    available -= 1
                    occupied += 1
                    results.append(
                        RecalculationResult(
                            entity_type="WAITLIST",
                            entity_id=entry_id,
                            student_id=student_id,
                            old_status="WAITING",
                            new_status="PROMOTED",
                            reason_code="ELIGIBLE",
                            details={"position_at_start": entry.get("position")},
                        )
                    )
                    summary.promoted += 1
                    await self._audit_transition(run, entry, "WAITLIST_PROMOTED", "PROMOTED", "ELIGIBLE")

                await self.repository.renumber_waitlist(run.course_id)
                summary.waiting += sum(1 for item in await self.repository.list_waiting(run.course_id))
                return await self.run_registry.transition(
                    run_id,
                    RunStatus.SUCCEEDED,
                    summary=summary,
                    results=results,
                )
            except Exception as exc:
                if snapshot is not None:
                    await self.repository.restore(snapshot)
                await self.run_registry.fail(run_id, str(exc), details=[{"type": type(exc).__name__}])
                raise

    async def _audit_transition(self, run: Any, entry: dict[str, Any], action: str, new_status: str, reason: str) -> None:
        if self.audit_writer is None:
            return
        course = await self.repository.get_course(run.course_id)
        course_snapshot = {
            "course_id": run.course_id,
            "course_code": str(course.get("code") or ""),
            "course_name": str(course.get("name") or course.get("code") or run.course_id),
        }
        record = build_audit_record(
            actor_id=run.operator_id or "system",
            actor_role=Role.ACADEMIC,
            action=action,
            resource_type="waitlist_entry",
            resource_id=str(entry["id"]),
            subject_student_id=str(entry["student_id"]),
            before_json={**course_snapshot, "status": "WAITING"},
            after_json={**course_snapshot, "status": new_status},
            reason=reason,
            run_id=run.id,
            request_id=f"run:{run.id}",
        )
        await self.audit_writer.append(record)
