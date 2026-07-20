import json
import socket
import subprocess
import sys
import time
import unittest
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


class AdminHttpApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.port = _free_port()
        cls.base_url = f"http://127.0.0.1:{cls.port}/api/v1"
        cls.server = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "app.main:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(cls.port),
                "--log-level",
                "warning",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if cls.server.poll() is not None:
                stdout, stderr = cls.server.communicate(timeout=1)
                raise RuntimeError(f"uvicorn exited early: {stdout}\n{stderr}")
            try:
                status, _ = cls.request_json("/health")
                if status == 200:
                    break
            except URLError:
                time.sleep(0.1)
        else:
            cls.server.terminate()
            raise RuntimeError("uvicorn did not become ready in 10 seconds")
        cls.academic_token = cls.login("academic", "academic123")
        cls.student_token = cls.login("student", "student123")

    @classmethod
    def tearDownClass(cls):
        cls.server.terminate()
        try:
            cls.server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            cls.server.kill()
            cls.server.wait(timeout=5)

    @classmethod
    def request_json(cls, path, *, method="GET", token=None, payload=None, headers=None):
        body = json.dumps(payload).encode() if payload is not None else None
        request_headers = {"Content-Type": "application/json", **(headers or {})}
        if token:
            request_headers["Authorization"] = f"Bearer {token}"
        request = Request(f"{cls.base_url}{path}", data=body, method=method, headers=request_headers)
        try:
            with urlopen(request, timeout=5) as response:
                return response.status, json.loads(response.read())
        except HTTPError as exc:
            return exc.code, json.loads(exc.read())

    @classmethod
    def login(cls, username, password):
        status, body = cls.request_json(
            "/auth/login",
            method="POST",
            payload={"username": username, "password": password},
        )
        if status != 200:
            raise RuntimeError(f"login failed: {status} {body}")
        return body["access_token"]

    def test_academic_rbac_statuses_and_success_envelope(self):
        anonymous_status, anonymous = self.request_json("/admin/courses")
        student_status, student = self.request_json("/admin/courses", token=self.student_token)
        academic_status, academic = self.request_json("/admin/courses", token=self.academic_token)

        self.assertEqual(anonymous_status, 401)
        self.assertIn("detail", anonymous)  # Shared auth envelope remains A-owned.
        self.assertEqual(student_status, 403)
        self.assertIn("detail", student)
        self.assertEqual(academic_status, 200)
        self.assertIsInstance(academic["data"], list)
        self.assertTrue(academic["meta"]["request_id"])

    def test_missing_course_returns_contract_error_envelope(self):
        status, body = self.request_json(
            "/admin/courses/course-missing/expand",
            method="POST",
            token=self.academic_token,
            payload={"capacity_delta": 1},
            headers={"X-Request-ID": "http-test-missing"},
        )
        self.assertEqual(status, 404)
        self.assertEqual(body["error"]["code"], "COURSE_NOT_FOUND")
        self.assertEqual(body["meta"]["request_id"], "http-test-missing")

    def test_course_change_preview_is_read_only_and_returns_impact_fields(self):
        _, before = self.request_json("/admin/courses?keyword=AI201", token=self.academic_token)
        course = before["data"][0]
        status, body = self.request_json(
            f"/admin/courses/{course['id']}/change-preview",
            method="POST",
            token=self.academic_token,
            payload={
                "operation": "UPDATE",
                "capacity": course["capacity"] + 1,
                "schedules": [{"weekday": 2, "start_minute": 600, "end_minute": 690, "room": "B202"}],
            },
        )
        _, after = self.request_json("/admin/courses?keyword=AI201", token=self.academic_token)

        self.assertEqual(status, 200)
        self.assertEqual(body["data"]["course_code"], "AI201")
        self.assertEqual(
            set(body["data"]),
            {"operation", "course_id", "course_code", "course_name", "enrolled_count", "promoted", "waiting", "conflicts", "errors"},
        )
        self.assertEqual(after["data"][0]["capacity"], course["capacity"])

    def test_idempotency_key_reuses_run_without_second_capacity_change(self):
        _, before = self.request_json("/admin/courses?keyword=SE301", token=self.academic_token)
        initial_capacity = before["data"][0]["capacity"]
        headers = {"Idempotency-Key": "http-test-expand-once", "X-Request-ID": "http-test-expand"}
        first_status, first = self.request_json(
            "/admin/courses/course-301/expand",
            method="POST",
            token=self.academic_token,
            payload={"capacity_delta": 1},
            headers=headers,
        )
        second_status, second = self.request_json(
            "/admin/courses/course-301/expand",
            method="POST",
            token=self.academic_token,
            payload={"capacity_delta": 1},
            headers=headers,
        )
        _, after = self.request_json("/admin/courses?keyword=SE301", token=self.academic_token)

        self.assertEqual(first_status, 200)
        self.assertEqual(second_status, 200)
        self.assertEqual(first["data"]["run"]["id"], second["data"]["run"]["id"])
        self.assertTrue(second["data"]["reused"])
        self.assertEqual(after["data"][0]["capacity"], initial_capacity + 1)

    def test_course_operations_require_approval_before_database_mutation(self):
        payload = {
            "code": "HTTP401",
            "name": "云原生架构",
            "teacher_name": "测试老师",
            "credits": 3,
            "capacity": 30,
            "schedules": [{"weekday": 4, "start_minute": 480, "end_minute": 570, "room": "D401"}],
            "prerequisites": ["course-101"],
        }
        create_status, created = self.request_json("/admin/courses", method="POST", token=self.academic_token, payload=payload)
        self.assertEqual(create_status, 200)
        self.assertIsNone(created["data"]["course"])
        self.assertEqual(created["data"]["operation"]["status"], "PENDING")
        _, pending_preview = self.request_json("/admin/courses?keyword=HTTP401&status=PENDING_APPROVAL", token=self.academic_token)
        self.assertEqual(pending_preview["data"][0]["status"], "PENDING_APPROVAL")
        _, open_courses = self.request_json("/admin/courses?keyword=HTTP401&status=OPEN", token=self.academic_token)
        self.assertEqual(open_courses["data"], [])
        _, operation_page = self.request_json("/admin/course-operation-approvals?status=PENDING", token=self.academic_token)
        operation = next(item for item in operation_page["data"] if item["id"] == created["data"]["operation"]["id"])
        approve_status, approved = self.request_json(f"/admin/course-operation-approvals/{operation['id']}/approve", method="POST", token=self.academic_token, payload={"comment": "批准新增课程"})
        self.assertEqual(approve_status, 200)
        course = approved["data"]["course"]
        self.assertEqual(course["teacher_name"], "测试老师")
        update_payload = {**payload, "capacity": 36, "schedules": [{"weekday": 5, "start_minute": 600, "end_minute": 690, "room": "D402"}]}
        update_status, updated = self.request_json(f"/admin/courses/{course['id']}", method="PATCH", token=self.academic_token, payload=update_payload)
        self.assertEqual(update_status, 200)
        self.assertIsNone(updated["data"]["course"])
        _, update_operations = self.request_json(f"/admin/course-operation-approvals?status=PENDING&course_id={course['id']}", token=self.academic_token)
        update_operation = update_operations["data"][0]
        approve_update_status, approved_update = self.request_json(f"/admin/course-operation-approvals/{update_operation['id']}/approve", method="POST", token=self.academic_token, payload={"comment": "批准编辑课程"})
        self.assertEqual(approve_update_status, 200)
        self.assertEqual(approved_update["data"]["course"]["capacity"], 36)
        self.assertEqual(approved_update["data"]["run"]["trigger_type"], "COURSE_UPDATE")
        audit_status, audit_page = self.request_json(f"/admin/audit-logs?course_id={course['id']}", token=self.academic_token)
        self.assertEqual(audit_status, 200)
        self.assertTrue({item["action"] for item in audit_page["data"]} >= {"COURSE_CREATED", "COURSE_UPDATED"})

    def test_rejected_course_operation_never_creates_course(self):
        payload = {
            "code": "HTTP-REJECT-401",
            "name": "应被驳回的课程",
            "teacher_name": "测试老师",
            "credits": 2,
            "capacity": 20,
            "schedules": [{"weekday": 2, "start_minute": 480, "end_minute": 570, "room": "R401"}],
            "prerequisites": [],
        }
        create_status, created = self.request_json("/admin/courses", method="POST", token=self.academic_token, payload=payload)
        self.assertEqual(create_status, 200)
        operation_id = created["data"]["operation"]["id"]

        reject_status, rejected = self.request_json(
            f"/admin/course-operation-approvals/{operation_id}/reject",
            method="POST",
            token=self.academic_token,
            payload={"comment": "课程信息不完整"},
        )
        self.assertEqual(reject_status, 200)
        self.assertEqual(rejected["data"]["operation"]["status"], "REJECTED")
        _, courses = self.request_json("/admin/courses?keyword=HTTP-REJECT-401", token=self.academic_token)
        self.assertEqual(courses["data"], [])

        second_status, second = self.request_json(
            f"/admin/course-operation-approvals/{operation_id}/approve",
            method="POST",
            token=self.academic_token,
            payload={"comment": "重复决定"},
        )
        self.assertEqual(second_status, 409)
        self.assertEqual(second["error"]["code"], "COURSE_OPERATION_NOT_PENDING")


if __name__ == "__main__":
    unittest.main()
