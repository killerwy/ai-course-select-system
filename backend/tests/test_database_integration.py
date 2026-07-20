"""Process-isolated MySQL-mode smoke test using SQLite as the SQL backend.

The isolation is intentional: the existing C contract tests exercise the
memory baseline, while this test starts a fresh interpreter with
``APP_STORAGE=database`` and therefore verifies the real SQLAlchemy route
selection without requiring a developer's MySQL server.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap


def test_database_mode_cross_role_smoke(tmp_path):
    db_path = tmp_path / "integration.sqlite3"
    script = textwrap.dedent(
        """
        import asyncio, hashlib, json, os
        from datetime import datetime, timezone
        from httpx import ASGITransport, AsyncClient
        os.environ["APP_STORAGE"] = "database"
        os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///" + os.environ["DB_PATH"]

        from app.database import Base, engine, async_session_factory
        from app.main import app
        from app.storage import get_optional_db
        from app.models import Course, CourseSchedule, CoursePrerequisite, Enrollment, ExceptionApproval, User, StudentProfile, WaitlistEntry

        def demo_hash(value):
            return "sha256$" + hashlib.sha256(value.encode()).hexdigest()

        async def seed():
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            async with async_session_factory() as session:
                session.add_all([
                    User(id="db-student", username="dbstudent", password_hash=demo_hash("student123"), role="STUDENT", status="ACTIVE"),
                    User(id="db-academic", username="dbacademic", password_hash=demo_hash("academic123"), role="ACADEMIC", status="ACTIVE"),
                ])
                session.add(StudentProfile(user_id="db-student", student_no="DB001", major="Computer Science", grade=2))
                session.add_all([
                    Course(id="db-101", code="DB101", name="Database Basics", credits=3, capacity=2, status="OPEN", version=1),
                    Course(id="db-201", code="DB201", name="Database Lab", credits=3, capacity=1, status="OPEN", version=1),
                ])
                await session.flush()
                session.add_all([
                    CourseSchedule(id="db-s-101", course_id="db-101", weekday=1, start_minute=480, end_minute=540, room="A"),
                    CourseSchedule(id="db-s-201", course_id="db-201", weekday=2, start_minute=480, end_minute=540, room="B"),
                    CoursePrerequisite(course_id="db-201", prerequisite_course_id="db-101", min_grade="D"),
                ])
                session.add(Enrollment(id="db-enroll-101", student_id="db-student", course_id="db-101", status="ENROLLED", source="DIRECT"))
                session.add(ExceptionApproval(id="db-approval", student_id="db-student", course_id="db-201", status="PENDING", rule_violations="[]", waived_rules="[]"))
                await session.commit()

        async def flow():
            await seed()
            async def override():
                async with async_session_factory() as session:
                    try:
                        yield session
                        await session.commit()
                    except Exception:
                        await session.rollback()
                        raise
            app.dependency_overrides[get_optional_db] = override
            transport = ASGITransport(app=app)
            async with AsyncClient(transport=transport, base_url="http://test") as client:
                health = await client.get("/api/v1/health")
                assert health.status_code == 200 and health.json()["data"]["database"] is True
                academic = (await client.post("/api/v1/auth/login", json={"username":"dbacademic","password":"academic123"})).json()["access_token"]
                student = (await client.post("/api/v1/auth/login", json={"username":"dbstudent","password":"student123"})).json()["access_token"]
                recommendation = await client.post("/api/v1/students/me/recommendations", headers={"Authorization": "Bearer " + student}, json={"goals":"数据库与人工智能","preferences":["实践"]})
                assert recommendation.status_code == 200 and recommendation.json()["data"]["status"] == "FALLBACK" and recommendation.json()["data"]["items"], (recommendation.status_code, recommendation.text)
                schedule = await client.get("/api/v1/students/me/schedule", headers={"Authorization": "Bearer " + student})
                assert schedule.status_code == 200 and {item["id"] for item in schedule.json()["data"]["courses"]} == {"db-101"}, (schedule.status_code, schedule.text)
                course_detail = await client.get("/api/v1/courses/db-101", headers={"Authorization": "Bearer " + student})
                assert course_detail.status_code == 200 and course_detail.json()["data"]["code"] == "DB101", (course_detail.status_code, course_detail.text)
                legacy_recommendation_input = await client.post("/api/v1/students/me/recommendations", headers={"Authorization": "Bearer " + student}, json={"goals":"数据库","completed_course_ids":[]})
                assert legacy_recommendation_input.status_code == 422, (legacy_recommendation_input.status_code, legacy_recommendation_input.text)
                create = await client.post("/api/v1/admin/courses", headers={"Authorization": "Bearer " + academic}, json={"code":"DB301","name":"Database Seminar","teacher_name":"DB Teacher","credits":2,"capacity":20,"schedules":[{"weekday":3,"start_minute":480,"end_minute":570,"room":"C"}],"prerequisites":["DB101"]})
                assert create.status_code == 200 and create.json()["data"]["course"] is None and create.json()["data"]["operation"]["status"] == "PENDING", (create.status_code, create.text)
                create_operation_id = create.json()["data"]["operation"]["id"]
                before_approval = await client.get("/api/v1/admin/courses?keyword=DB301&status=PENDING_APPROVAL", headers={"Authorization": "Bearer " + academic})
                assert before_approval.status_code == 200 and before_approval.json()["data"][0]["status"] == "PENDING_APPROVAL", (before_approval.status_code, before_approval.text)
                approved_create = await client.post("/api/v1/admin/course-operation-approvals/" + create_operation_id + "/approve", headers={"Authorization": "Bearer " + academic}, json={"comment":"批准新增课程"})
                assert approved_create.status_code == 200 and approved_create.json()["data"]["course"]["teacher_name"] == "DB Teacher" and approved_create.json()["data"]["course"]["prerequisites"] == ["db-101"], (approved_create.status_code, approved_create.text)
                created_id = approved_create.json()["data"]["course"]["id"]
                preview = await client.post("/api/v1/admin/courses/" + created_id + "/change-preview", headers={"Authorization": "Bearer " + academic}, json={"operation":"UPDATE","capacity":25,"schedules":[{"weekday":4,"start_minute":600,"end_minute":690,"room":"D"}]})
                assert preview.status_code == 200 and preview.json()["data"]["course_code"] == "DB301" and preview.json()["data"]["conflicts"] == 0, (preview.status_code, preview.text)
                student_catalog_after_create = await client.get("/api/v1/courses?keyword=DB301", headers={"Authorization": "Bearer " + student})
                assert student_catalog_after_create.status_code == 200 and student_catalog_after_create.json()["data"][0]["teacher_name"] == "DB Teacher", (student_catalog_after_create.status_code, student_catalog_after_create.text)
                duplicate_create = await client.post("/api/v1/admin/courses", headers={"Authorization": "Bearer " + academic}, json={"code":"DB301","name":"Database Seminar Copy","teacher_name":"DB Teacher","credits":2,"capacity":20,"schedules":[{"weekday":3,"start_minute":480,"end_minute":570,"room":"C"}],"prerequisites":[]})
                assert duplicate_create.status_code == 409 and duplicate_create.json()["error"]["code"] == "COURSE_ALREADY_EXISTS", (duplicate_create.status_code, duplicate_create.text)
                invalid_prerequisite = await client.post("/api/v1/admin/courses", headers={"Authorization": "Bearer " + academic}, json={"code":"DB302","name":"Missing Prerequisite","teacher_name":"DB Teacher","credits":2,"capacity":20,"schedules":[{"weekday":3,"start_minute":480,"end_minute":570,"room":"C"}],"prerequisites":["DOES-NOT-EXIST"]})
                assert invalid_prerequisite.status_code == 422 and invalid_prerequisite.json()["error"]["code"] == "PREREQUISITE_NOT_FOUND", (invalid_prerequisite.status_code, invalid_prerequisite.text)
                update = await client.patch("/api/v1/admin/courses/" + created_id, headers={"Authorization": "Bearer " + academic, "Idempotency-Key": "db-update-course"}, json={"code":"DB301","name":"Database Seminar","teacher_name":"DB Teacher 2","credits":2,"capacity":25,"schedules":[{"weekday":4,"start_minute":600,"end_minute":690,"room":"D"}],"prerequisites":["DB101"]})
                assert update.status_code == 200 and update.json()["data"]["course"] is None and update.json()["data"]["operation"]["status"] == "PENDING", (update.status_code, update.text)
                update_operation_id = update.json()["data"]["operation"]["id"]
                approved_update = await client.post("/api/v1/admin/course-operation-approvals/" + update_operation_id + "/approve", headers={"Authorization": "Bearer " + academic}, json={"comment":"批准编辑课程"})
                assert approved_update.status_code == 200 and approved_update.json()["data"]["course"]["teacher_name"] == "DB Teacher 2" and approved_update.json()["data"]["run"]["status"] == "SUCCEEDED", (approved_update.status_code, approved_update.text)
                student_catalog_after_update = await client.get("/api/v1/courses?keyword=DB301", headers={"Authorization": "Bearer " + student})
                assert student_catalog_after_update.status_code == 200 and student_catalog_after_update.json()["data"][0]["teacher_name"] == "DB Teacher 2", (student_catalog_after_update.status_code, student_catalog_after_update.text)
                oversized_cancel_key = "cancel-" + created_id + "-" + ("x" * 40)
                oversized_cancel = await client.post("/api/v1/admin/courses/" + created_id + "/cancel", headers={"Authorization": "Bearer " + academic, "Idempotency-Key": oversized_cancel_key}, json={"reason":"边界测试"})
                assert oversized_cancel.status_code == 422 and oversized_cancel.json()["error"]["code"] == "INVALID_IDEMPOTENCY_KEY", (oversized_cancel.status_code, oversized_cancel.text)
                cancel = await client.post("/api/v1/admin/courses/" + created_id + "/cancel", headers={"Authorization": "Bearer " + academic, "Idempotency-Key": "cancel-" + created_id}, json={"reason":"课程安排调整"})
                assert cancel.status_code == 200 and cancel.json()["data"]["course"] is None and cancel.json()["data"]["operation"]["status"] == "PENDING", (cancel.status_code, cancel.text)
                cancel_operation_id = cancel.json()["data"]["operation"]["id"]
                approved_cancel = await client.post("/api/v1/admin/course-operation-approvals/" + cancel_operation_id + "/approve", headers={"Authorization": "Bearer " + academic}, json={"comment":"批准取消课程"})
                assert approved_cancel.status_code == 200 and approved_cancel.json()["data"]["course"] is None and approved_cancel.json()["data"]["run"]["status"] == "SUCCEEDED", (approved_cancel.status_code, approved_cancel.text)
                deleted_course = await client.get("/api/v1/admin/courses?keyword=DB301", headers={"Authorization": "Bearer " + academic})
                assert deleted_course.status_code == 200 and deleted_course.json()["data"] == [], (deleted_course.status_code, deleted_course.text)
                student_catalog_after_cancel = await client.get("/api/v1/courses?keyword=DB301", headers={"Authorization": "Bearer " + student})
                assert student_catalog_after_cancel.status_code == 200 and student_catalog_after_cancel.json()["data"] == [], (student_catalog_after_cancel.status_code, student_catalog_after_cancel.text)
                headers = {"Authorization": "Bearer " + academic, "Idempotency-Key": "db-expand-once"}
                first = await client.post("/api/v1/admin/courses/db-201/expand", headers=headers, json={"capacity_delta": 1})
                second = await client.post("/api/v1/admin/courses/db-201/expand", headers=headers, json={"capacity_delta": 1})
                assert first.status_code == 200 and first.json()["data"]["run"]["status"] == "SUCCEEDED", (first.status_code, first.text)
                assert second.status_code == 200 and second.json()["data"]["reused"] is True, (second.status_code, second.text)
                run_id = first.json()["data"]["run"]["id"]
                polled = await client.get("/api/v1/admin/recalculation-runs/" + run_id, headers={"Authorization": "Bearer " + academic})
                assert polled.status_code == 200 and polled.json()["data"]["status"] == "SUCCEEDED", (polled.status_code, polled.text)
                approvals = await client.get("/api/v1/admin/exception-approvals", headers={"Authorization": "Bearer " + academic})
                assert approvals.status_code == 200 and approvals.json()["meta"]["total"] == 1, (approvals.status_code, approvals.text)
                approved = await client.post("/api/v1/admin/exception-approvals/db-approval/approve", headers={"Authorization": "Bearer " + academic}, json={"comment":"核验通过","waived_rules":[]})
                assert approved.status_code == 200 and approved.json().get("data", {}).get("status") == "APPROVED", (approved.status_code, approved.text)
                audits = await client.get("/api/v1/admin/audit-logs?student_id=db-student", headers={"Authorization": "Bearer " + academic})
                assert audits.status_code == 200 and audits.json()["meta"]["total"] >= 1, (audits.status_code, audits.text)
                bad_capacity = await client.post("/api/v1/admin/courses/db-201/expand", headers={"Authorization": "Bearer " + academic}, json={"capacity_delta": 0})
                assert bad_capacity.status_code == 422, (bad_capacity.status_code, bad_capacity.text)
                missing = await client.post("/api/v1/admin/courses/missing/expand", headers={"Authorization": "Bearer " + academic}, json={"capacity_delta": 1})
                assert missing.status_code == 404, (missing.status_code, missing.text)
                enrollments = await client.get("/api/v1/students/me/enrollments", headers={"Authorization": "Bearer " + student})
                assert enrollments.status_code == 200 and {item["course_id"] for item in enrollments.json()["data"]} == {"db-101", "db-201"}, (enrollments.status_code, enrollments.text)
            app.dependency_overrides.clear()
            await engine.dispose()
            print(json.dumps({"health": health.status_code, "run": run_id, "idempotent": True}))

        asyncio.run(flow())
        """
    )
    env = os.environ.copy()
    env["DB_PATH"] = str(db_path).replace("\\", "/")
    env["DEEPSEEK_API_KEY"] = ""
    completed = subprocess.run([sys.executable, "-c", script], cwd=os.path.dirname(os.path.dirname(__file__)), env=env, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stdout + "\n" + completed.stderr
    assert '"idempotent": true' in completed.stdout
