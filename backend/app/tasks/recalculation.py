from __future__ import annotations

from typing import Any


class RecalculationTaskRunner:
    """Translate background execution into a terminal run owned by the service."""

    def __init__(self, recalculation_service: Any, run_registry: Any) -> None:
        self.recalculation_service = recalculation_service
        self.run_registry = run_registry

    async def run(self, run_id: str):
        try:
            return await self.recalculation_service.execute(run_id)
        except Exception:
            # The service owns FAILED transition and rollback. Returning the
            # terminal record keeps BackgroundTasks from swallowing the run id.
            return await self.run_registry.get(run_id)


def enqueue_recalculation(background_tasks: Any, runner: RecalculationTaskRunner, run_id: str) -> str:
    """Register one idempotent task and return the run id for polling."""

    background_tasks.add_task(runner.run, run_id)
    return run_id

