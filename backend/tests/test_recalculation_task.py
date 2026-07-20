"""Tests for RecalculationTaskRunner and enqueue_recalculation."""

import pytest

from app.tasks.recalculation import RecalculationTaskRunner, enqueue_recalculation


class FakeBackgroundTasks:
    def __init__(self):
        self.calls = []

    def add_task(self, function, *args, **kwargs):
        self.calls.append((function, args, kwargs))


class FakeService:
    async def execute(self, run_id):
        return {"run_id": run_id, "status": "SUCCEEDED"}


class FakeRegistry:
    async def get(self, run_id):
        return {"run_id": run_id, "status": "FAILED"}


def test_enqueue_registers_one_run_id_task():
    """enqueue_recalculation adds one task with the run ID."""
    tasks = FakeBackgroundTasks()
    runner = RecalculationTaskRunner(FakeService(), FakeRegistry())
    result = enqueue_recalculation(tasks, runner, "run-001")
    assert result == "run-001"
    assert len(tasks.calls) == 1
    assert tasks.calls[0][1] == ("run-001",)


@pytest.mark.asyncio
async def test_runner_returns_service_result():
    """Runner returns the service execution result."""
    runner = RecalculationTaskRunner(FakeService(), FakeRegistry())
    result = await runner.run("run-001")
    assert result["status"] == "SUCCEEDED"


@pytest.mark.asyncio
async def test_runner_returns_terminal_record_after_service_failure():
    """Runner returns FAILED status when service raises an exception."""

    class FailingService:
        async def execute(self, run_id):
            raise RuntimeError("worker failed")

    runner = RecalculationTaskRunner(FailingService(), FakeRegistry())
    result = await runner.run("run-001")
    assert result["status"] == "FAILED"
