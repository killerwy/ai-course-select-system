"""Tests for RecalculationService."""

import pytest

from app.ports.admin import RuleResult
from app.schemas.admin import RunStatus, TriggerType
from app.services.in_memory import InMemoryAdminRepository, InMemoryAuditWriter
from app.services.recalculation import RecalculationService
from app.services.runs import RunRegistry


class FakeRuleChecker:
    def __init__(self, results):
        self.results = results
        self.calls = []

    async def check_enrollment(self, student_id, course_id, *, waived_rules=None) -> RuleResult:
        self.calls.append((student_id, course_id))
        return self.results[student_id]


def build_service(*, rule_results, capacity=2, enrollments=None, waitlists=None):
    repository = InMemoryAdminRepository(
        courses=[{"id": "course-201", "capacity": capacity, "status": "OPEN"}],
        enrollments=enrollments or [],
        waitlists=waitlists or [],
    )
    audit_writer = InMemoryAuditWriter()
    registry = RunRegistry(id_factory=lambda: "run-test-001")
    service = RecalculationService(
        repository=repository,
        rule_checker=FakeRuleChecker(rule_results),
        audit_writer=audit_writer,
        run_registry=registry,
    )
    return repository, audit_writer, registry, service


@pytest.mark.asyncio
async def test_skips_first_invalid_candidate_and_promotes_next():
    """Skips invalid candidates and promotes the next eligible one."""
    repository, audit_writer, registry, service = build_service(
        rule_results={
            "student-001": {"eligible": False, "decision": "CONFLICT", "violations": [{"code": "TIME_CONFLICT", "blocking": True}], "warnings": [], "checked_at": "now"},
            "student-002": {"eligible": True, "decision": "ELIGIBLE", "violations": [], "warnings": [], "checked_at": "now"},
        },
        capacity=2,
        enrollments=[{"student_id": "student-900", "course_id": "course-201", "status": "ENROLLED"}],
        waitlists=[
            {"id": "wait-001", "student_id": "student-001", "course_id": "course-201", "status": "WAITING", "position": 1, "joined_at": "2026-07-16T06:00:00+00:00"},
            {"id": "wait-002", "student_id": "student-002", "course_id": "course-201", "status": "WAITING", "position": 2, "joined_at": "2026-07-16T06:01:00+00:00"},
        ],
    )
    run, _ = await registry.start(course_id="course-201", trigger_type=TriggerType.EXPAND, operator_id="academic-001")
    done = await service.execute(run.id)
    assert done.status == RunStatus.SUCCEEDED
    assert done.summary.skipped == 1
    assert done.summary.promoted == 1
    assert repository.waitlists["wait-001"]["status"] == "SKIPPED"
    assert repository.waitlists["wait-002"]["status"] == "PROMOTED"
    assert repository.enrollments[("student-002", "course-201")]["status"] == "ENROLLED"
    assert len(audit_writer.records) == 2


@pytest.mark.asyncio
async def test_no_capacity_keeps_eligible_candidates_waiting():
    """Eligible candidates stay waiting when course is at capacity."""
    repository, _, registry, service = build_service(
        rule_results={"student-001": {"eligible": True, "decision": "ELIGIBLE", "violations": [], "warnings": [], "checked_at": "now"}},
        capacity=1,
        enrollments=[{"student_id": "student-900", "course_id": "course-201", "status": "ENROLLED"}],
        waitlists=[{"id": "wait-001", "student_id": "student-001", "course_id": "course-201", "status": "WAITING", "position": 1, "joined_at": "2026-07-16T06:00:00+00:00"}],
    )
    run, _ = await registry.start(course_id="course-201", trigger_type=TriggerType.MANUAL, operator_id="academic-001")
    done = await service.execute(run.id)
    assert done.results[0].new_status == "WAITING"
    assert repository.waitlists["wait-001"]["status"] == "WAITING"
    assert repository.waitlists["wait-001"]["position"] == 1


@pytest.mark.asyncio
async def test_rule_checker_failure_rolls_back_partial_mutations_and_fails_run():
    """Rule checker failure rolls back mutations and fails the run."""

    class FailingRuleChecker(FakeRuleChecker):
        async def check_enrollment(self, student_id, course_id, *, waived_rules=None):
            if student_id == "student-002":
                raise RuntimeError("rule service unavailable")
            return await super().check_enrollment(student_id, course_id, waived_rules=waived_rules)

    repository = InMemoryAdminRepository(
        courses=[{"id": "course-201", "capacity": 2, "status": "OPEN"}],
        enrollments=[{"student_id": "student-900", "course_id": "course-201", "status": "ENROLLED"}],
        waitlists=[
            {"id": "wait-001", "student_id": "student-001", "course_id": "course-201", "status": "WAITING", "position": 1, "joined_at": "2026-07-16T06:00:00+00:00"},
            {"id": "wait-002", "student_id": "student-002", "course_id": "course-201", "status": "WAITING", "position": 2, "joined_at": "2026-07-16T06:01:00+00:00"},
        ],
    )
    snapshot = await repository.snapshot()
    registry = RunRegistry(id_factory=lambda: "run-test-002")
    service = RecalculationService(
        repository=repository,
        rule_checker=FailingRuleChecker({"student-001": {"eligible": True, "decision": "ELIGIBLE", "violations": [], "warnings": [], "checked_at": "now"}}),
        audit_writer=InMemoryAuditWriter(),
        run_registry=registry,
    )
    run, _ = await registry.start(course_id="course-201", trigger_type=TriggerType.MANUAL, operator_id="academic-001")
    with pytest.raises(RuntimeError):
        await service.execute(run.id)
    failed = await registry.get(run.id)
    assert failed.status == RunStatus.FAILED
    assert await repository.snapshot() == snapshot


@pytest.mark.asyncio
async def test_cancelled_course_fails_without_changing_waitlist():
    """Cancelled course fails without changing waitlist status."""
    repository, _, registry, service = build_service(
        rule_results={},
        waitlists=[{"id": "wait-001", "student_id": "student-001", "course_id": "course-201", "status": "WAITING", "position": 1, "joined_at": "2026-07-16T06:00:00+00:00"}],
    )
    repository.courses["course-201"]["status"] = "CANCELLED"
    run, _ = await registry.start(course_id="course-201", trigger_type=TriggerType.MANUAL, operator_id="academic-001")
    with pytest.raises(ValueError):
        await service.execute(run.id)
    assert (await registry.get(run.id)).status == RunStatus.FAILED
    assert repository.waitlists["wait-001"]["status"] == "WAITING"
