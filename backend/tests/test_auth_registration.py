from __future__ import annotations

from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.database import Base
from app.main import app
from app.models import AuditLog
from app.services.database_store import _write_audit, authenticate, register_student


@pytest.mark.anyio
async def test_student_registration_creates_account_and_keeps_enrollments_isolated() -> None:
    suffix = uuid4().hex[:8]
    first_payload = {
        "username": f"student-{suffix}-a",
        "password": "student-pass-1",
        "student_no": f"REG{suffix}A",
        "major": "计算机科学",
        "grade": 2,
    }
    second_payload = {**first_payload, "username": f"student-{suffix}-b", "student_no": f"REG{suffix}B"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post("/api/v1/auth/register", json=first_payload)
        second = await client.post("/api/v1/auth/register", json=second_payload)
        assert first.status_code == 201
        assert second.status_code == 201
        assert first.json()["user"]["role"] == "STUDENT"
        assert first.json()["user"]["id"] != second.json()["user"]["id"]

        duplicate = await client.post("/api/v1/auth/register", json=first_payload)
        assert duplicate.status_code == 409

        first_token = first.json()["access_token"]
        second_token = second.json()["access_token"]
        enrolled = await client.post(
            "/api/v1/students/me/enrollment-requests",
            headers={"Authorization": f"Bearer {first_token}"},
            json={"course_id": "course-301", "type": "ENROLL"},
        )
        assert enrolled.status_code == 200

        first_schedule = await client.get(
            "/api/v1/students/me/schedule", headers={"Authorization": f"Bearer {first_token}"}
        )
        second_schedule = await client.get(
            "/api/v1/students/me/schedule", headers={"Authorization": f"Bearer {second_token}"}
        )
        assert {course["id"] for course in first_schedule.json()["data"]["courses"]} == {"course-301"}
        assert second_schedule.json()["data"]["courses"] == []


@pytest.mark.anyio
async def test_database_registration_persists_user_and_profile() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    async with session_factory() as session:
        created = await register_student(
            session,
            username="db-register-user",
            password="db-pass-1",
            student_no="DB-REGISTER-1",
            major="软件工程",
            grade=3,
        )
        await session.commit()
        logged_in = await authenticate(session, "db-register-user", "db-pass-1")
        assert logged_in is not None
        assert logged_in["user"]["id"] == created["user"]["id"]
        assert logged_in["user"]["student_no"] == "DB-REGISTER-1"
    await engine.dispose()


@pytest.mark.anyio
async def test_database_audit_compacts_uuid_enrollment_request_id() -> None:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    long_request_id = f"student:{uuid4()}:{uuid4()}"
    async with session_factory() as session:
        await _write_audit(
            session,
            actor_id="student-audit-test",
            actor_role="STUDENT",
            action="ENROLLMENT_CREATED",
            resource_type="enrollment",
            resource_id="enrollment-audit-test",
            request_id=long_request_id,
        )
        await session.commit()
        record = (await session.execute(select(AuditLog))).scalar_one()
        assert len(record.request_id) <= 64
    await engine.dispose()
