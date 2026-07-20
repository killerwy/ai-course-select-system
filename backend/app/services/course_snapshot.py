from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Protocol

from ..store import InMemoryStore

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def schedules_overlap(first: dict, second: dict) -> bool:
    return (
        first["weekday"] == second["weekday"]
        and first["start_minute"] < second["end_minute"]
        and second["start_minute"] < first["end_minute"]
    )


def conflicting_selected_courses(snapshot: dict, course_id: str) -> list[dict]:
    candidate = next((course for course in snapshot.get("catalog", []) if course["id"] == course_id), None)
    if not candidate:
        return []
    return [
        selected
        for selected in snapshot.get("selected_courses", [])
        if selected["id"] != course_id
        and any(
            schedules_overlap(candidate_slot, selected_slot)
            for candidate_slot in candidate.get("schedules", [])
            for selected_slot in selected.get("schedules", [])
        )
    ]


class SnapshotCache(Protocol):
    backend: str

    async def set(self, key: str, value: dict) -> None: ...
    async def get(self, key: str) -> dict | None: ...


class MemorySnapshotCache:
    backend = "memory"

    def __init__(self) -> None:
        self.values: dict[str, dict] = {}

    async def set(self, key: str, value: dict) -> None:
        self.values[key] = json.loads(json.dumps(value, ensure_ascii=False, default=str))

    async def get(self, key: str) -> dict | None:
        value = self.values.get(key)
        return json.loads(json.dumps(value, ensure_ascii=False)) if value else None


class RedisBackedSnapshotCache:
    """Use Redis when configured; retain an in-process fallback for local runs."""

    def __init__(self, redis_url: str | None = None, ttl_seconds: int | None = None, redis_client: Any | None = None) -> None:
        self.memory = MemorySnapshotCache()
        self.backend = "memory"
        self.ttl_seconds = ttl_seconds or int(os.getenv("COURSE_SNAPSHOT_TTL_SECONDS", "300"))
        url = (redis_url if redis_url is not None else os.getenv("REDIS_URL", "")).strip()
        self.redis = redis_client
        if url and self.redis is None:
            try:
                from redis.asyncio import Redis

                self.redis = Redis.from_url(url, decode_responses=True, socket_connect_timeout=0.25, socket_timeout=0.25)
            except ImportError:
                self.redis = None

    async def set(self, key: str, value: dict) -> None:
        await self.memory.set(key, value)
        if not self.redis:
            self.backend = "memory"
            return
        try:
            await self.redis.set(key, json.dumps(value, ensure_ascii=False, default=str), ex=self.ttl_seconds)
            self.backend = "redis"
        except Exception:
            self.backend = "memory"
            self.redis = None
            logger.warning("Redis 课程快照不可用，本进程回退到内存缓存")

    async def get(self, key: str) -> dict | None:
        if self.redis:
            try:
                value = await self.redis.get(key)
                if value:
                    self.backend = "redis"
                    return json.loads(value)
            except Exception:
                self.backend = "memory"
                self.redis = None
                logger.warning("Redis 课程快照读取失败，本进程回退到内存缓存")
        return await self.memory.get(key)


class CourseSnapshotService:
    def __init__(self, cache: SnapshotCache | None = None) -> None:
        self.cache = cache or RedisBackedSnapshotCache()

    @staticmethod
    def key(student_id: str) -> str:
        return f"course-snapshot:{student_id}"

    def build(self, student_id: str, store: InMemoryStore) -> dict[str, Any]:
        catalog = []
        for course in store.courses.values():
            catalog.append(
                {
                    **course,
                    "enrolled_count": sum(
                        1
                        for record in store.enrollments.values()
                        if record["course_id"] == course["id"] and record["status"] in {"ENROLLED", "CONFLICT_REVIEW"}
                    ),
                    "waitlist_count": sum(
                        1
                        for record in store.waitlists.values()
                        if record["course_id"] == course["id"] and record["status"] == "WAITING"
                    ),
                }
            )
        selected_ids = {
            record["course_id"]
            for record in store.enrollments.values()
            if record["student_id"] == student_id and record["status"] in {"ENROLLED", "CONFLICT_REVIEW"}
        }
        return {
            "student_id": student_id,
            "catalog": catalog,
            "selected_courses": [course for course in catalog if course["id"] in selected_ids],
            "generated_at": _now(),
        }

    async def refresh(self, student_id: str, store: InMemoryStore) -> dict:
        snapshot = self.build(student_id, store)
        key = self.key(student_id)
        await self.cache.set(key, snapshot)
        return await self.cache.get(key) or snapshot


SNAPSHOT_SERVICE = CourseSnapshotService()
