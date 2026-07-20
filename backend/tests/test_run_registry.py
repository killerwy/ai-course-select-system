"""Tests for RunRegistry lifecycle management."""

import pytest

from app.schemas.admin import RunStatus, TriggerType
from app.services.runs import (
    InvalidRunTransitionError,
    RunAlreadyActiveError,
    RunNotFoundError,
    RunRegistry,
)


@pytest.fixture
def registry() -> RunRegistry:
    """Create a RunRegistry with a deterministic ID factory."""
    counter = iter(range(1, 10))
    return RunRegistry(id_factory=lambda: f"run-test-{next(counter)}")


@pytest.mark.asyncio
async def test_start_and_idempotent_replay_return_same_run(registry: RunRegistry):
    """Starting with the same idempotency key returns the same run."""
    first, reused_first = await registry.start(
        course_id="course-201",
        trigger_type=TriggerType.EXPAND,
        operator_id="academic-001",
        idempotency_key="idem-001",
    )
    second, reused_second = await registry.start(
        course_id="course-201",
        trigger_type=TriggerType.EXPAND,
        operator_id="academic-001",
        idempotency_key="idem-001",
    )
    assert not reused_first
    assert reused_second
    assert first.id == second.id
    assert first.status == RunStatus.PENDING


@pytest.mark.asyncio
async def test_active_run_blocks_different_key(registry: RunRegistry):
    """An active run blocks new runs with different idempotency keys."""
    await registry.start(
        course_id="course-201",
        trigger_type=TriggerType.MANUAL,
        operator_id="academic-001",
        idempotency_key="idem-001",
    )
    with pytest.raises(RunAlreadyActiveError):
        await registry.start(
            course_id="course-201",
            trigger_type=TriggerType.MANUAL,
            operator_id="academic-001",
            idempotency_key="idem-002",
        )


@pytest.mark.asyncio
async def test_valid_lifecycle_releases_course_for_new_run(registry: RunRegistry):
    """Completing a run allows starting a new one for the same course."""
    first, _ = await registry.start(
        course_id="course-201",
        trigger_type=TriggerType.MANUAL,
        operator_id="academic-001",
    )
    running = await registry.transition(first.id, RunStatus.RUNNING)
    done = await registry.transition(running.id, RunStatus.SUCCEEDED)
    assert done.status == RunStatus.SUCCEEDED

    next_run, reused = await registry.start(
        course_id="course-201",
        trigger_type=TriggerType.MANUAL,
        operator_id="academic-001",
    )
    assert next_run.id != first.id
    assert not reused


@pytest.mark.asyncio
async def test_invalid_transition_and_missing_run_are_explicit(registry: RunRegistry):
    """Invalid transitions and missing runs raise explicit errors."""
    run, _ = await registry.start(
        course_id="course-301",
        trigger_type=TriggerType.MANUAL,
        operator_id="academic-001",
    )
    with pytest.raises(InvalidRunTransitionError):
        await registry.transition(run.id, RunStatus.SUCCEEDED)
    with pytest.raises(RunNotFoundError):
        await registry.get("run-missing")


@pytest.mark.asyncio
async def test_failed_run_is_terminal_and_can_be_retried(registry: RunRegistry):
    """Failed runs are terminal but can be retried with a new run."""
    run, _ = await registry.start(
        course_id="course-301",
        trigger_type=TriggerType.MANUAL,
        operator_id="academic-001",
    )
    await registry.transition(run.id, RunStatus.RUNNING)
    failed = await registry.fail(run.id, "模拟规则服务失败")
    assert failed.status == RunStatus.FAILED
    assert failed.error.code == "RECALCULATION_FAILED"

    retry, _ = await registry.start(
        course_id="course-301",
        trigger_type=TriggerType.MANUAL,
        operator_id="academic-001",
        idempotency_key="retry-001",
    )
    assert retry.id != failed.id
