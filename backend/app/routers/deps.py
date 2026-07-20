"""Dependency injection container for FastAPI routers.

This module provides dependency functions that resolve to the appropriate
service implementation based on the storage mode (memory or database).
"""

from __future__ import annotations

from typing import Any

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..storage import get_optional_db
from ..store import STORE


def _sync_run(run: Any) -> None:
    """Sync run state to in-memory store."""
    STORE.runs[run.id] = run.model_dump(mode="json") if hasattr(run, "model_dump") else run


def get_admin_service(db: AsyncSession | None = Depends(get_optional_db)) -> Any:
    """Resolve admin service based on storage mode."""
    if db is not None and hasattr(db, "execute"):
        from ..services.database_admin import DatabaseAdminService
        return DatabaseAdminService(db)
    
    from ..services.store_adapter import StoreAdminRepository
    return StoreAdminRepository()


def get_enrollment_service(db: AsyncSession | None = Depends(get_optional_db)) -> Any:
    """Resolve enrollment service based on storage mode."""
    if db is not None and hasattr(db, "execute"):
        from ..services.enrollment_service import (
            check_enrollment,
            process_enrollment_request,
            list_student_enrollments,
            list_student_waitlists,
            list_student_schedule,
            list_student_audits,
        )
        return EnrollmentDBService(db)
    
    from ..services.store_adapter import StoreAdminRepository
    return StoreAdminRepository()


def get_recommendation_service(db: AsyncSession | None = Depends(get_optional_db)) -> Any:
    """Resolve recommendation service based on storage mode."""
    if db is not None and hasattr(db, "execute"):
        from ..services.recommendation_service_db import create_recommendation, get_recommendation
        return RecommendationDBService(db)
    
    from ..services.recommendation import RecommendationService
    from ..services.store_adapter import StoreAdminRepository
    return RecommendationService(repository=StoreAdminRepository())


def get_course_query_service(db: AsyncSession | None = Depends(get_optional_db)) -> Any:
    """Resolve course query service based on storage mode."""
    if db is not None and hasattr(db, "execute"):
        from ..services.course_query_service import list_course_summaries
        return CourseQueryDBService(db)
    
    from ..services.store_adapter import StoreAdminRepository
    return StoreAdminRepository()


def get_auth_service(db: AsyncSession | None = Depends(get_optional_db)) -> Any:
    """Resolve auth service based on storage mode."""
    if db is not None and hasattr(db, "execute"):
        from ..services.auth_service import authenticate, register_student, get_user_from_token
        return AuthDBService(db)
    
    from ..store import STORE
    return MemoryAuthService(STORE)


class EnrollmentDBService:
    """Wrapper for DB enrollment service."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def check_enrollment(self, student_id: str, course_id: str, **kwargs) -> dict:
        from ..services.enrollment_service import check_enrollment
        return await check_enrollment(self.session, student_id, course_id, **kwargs)
    
    async def process_enrollment_request(self, **kwargs) -> dict:
        from ..services.enrollment_service import process_enrollment_request
        return await process_enrollment_request(self.session, **kwargs)
    
    async def list_student_enrollments(self, student_id: str) -> list[dict]:
        from ..services.enrollment_service import list_student_enrollments
        return await list_student_enrollments(self.session, student_id)
    
    async def list_student_waitlists(self, student_id: str) -> list[dict]:
        from ..services.enrollment_service import list_student_waitlists
        return await list_student_waitlists(self.session, student_id)
    
    async def list_student_schedule(self, student_id: str) -> dict:
        from ..services.enrollment_service import list_student_schedule
        return await list_student_schedule(self.session, student_id)
    
    async def list_student_audits(self, student_id: str) -> list[dict]:
        from ..services.enrollment_service import list_student_audits
        return await list_student_audits(self.session, student_id)


class RecommendationDBService:
    """Wrapper for DB recommendation service."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create_recommendation(self, student_id: str, payload: Any) -> dict:
        from ..services.recommendation_service_db import create_recommendation
        return await create_recommendation(self.session, student_id, payload)
    
    async def get_recommendation(self, student_id: str, session_id: str) -> dict | None:
        from ..services.recommendation_service_db import get_recommendation
        return await get_recommendation(self.session, student_id, session_id)


class CourseQueryDBService:
    """Wrapper for DB course query service."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def list_courses(self, **kwargs) -> list[dict]:
        from ..services.course_query_service import list_course_summaries
        return await list_course_summaries(self.session, **kwargs)


class AuthDBService:
    """Wrapper for DB auth service."""
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def authenticate(self, username: str, password: str) -> dict | None:
        from ..services.auth_service import authenticate
        return await authenticate(self.session, username, password)
    
    async def register_student(self, **kwargs) -> dict:
        from ..services.auth_service import register_student
        return await register_student(self.session, **kwargs)
    
    async def get_user_from_token(self, token: str) -> dict | None:
        from ..services.auth_service import get_user_from_token
        return await get_user_from_token(self.session, token)


class MemoryAuthService:
    """Wrapper for memory auth service."""
    
    def __init__(self, store: Any):
        self.store = store
    
    async def authenticate(self, username: str, password: str) -> dict | None:
        from ..auth import create_access_token, verify_password
        user = next((u for u in self.store.users.values() if u.get("username") == username), None)
        if user is None or user.get("status") != "ACTIVE" or not verify_password(password, user.get("password_hash", "")):
            return None
        profile = self.store.profiles.get(user["id"])
        return {
            "access_token": create_access_token(user["id"], user["role"]),
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
                "student_no": profile.get("student_no") if profile else None,
                "major": profile.get("major") if profile else None,
                "grade": profile.get("grade") if profile else None,
            },
        }
    
    async def register_student(self, **kwargs) -> dict:
        from ..auth import create_access_token, hash_password
        from ..store import _uuid
        username = kwargs.get("username")
        password = kwargs.get("password")
        student_no = kwargs.get("student_no")
        major = kwargs.get("major", "")
        grade = kwargs.get("grade", 1)
        
        existing_username = next((u for u in self.store.users.values() if u.get("username", "").lower() == username.lower()), None)
        if existing_username:
            raise ValueError("USERNAME_EXISTS")
        existing_student_no = next((p for p in self.store.profiles.values() if p.get("student_no") == student_no), None)
        if existing_student_no:
            raise ValueError("STUDENT_NO_EXISTS")
        
        user_id = _uuid()
        self.store.users[user_id] = {
            "id": user_id,
            "username": username,
            "password_hash": hash_password(password),
            "role": "STUDENT",
            "status": "ACTIVE",
        }
        self.store.profiles[user_id] = {
            "user_id": user_id,
            "student_no": student_no,
            "major": major,
            "grade": grade,
        }
        return {
            "access_token": create_access_token(user_id, "STUDENT"),
            "token_type": "bearer",
            "user": {"id": user_id, "username": username, "role": "STUDENT", "student_no": student_no, "major": major, "grade": grade},
        }
    
    async def get_user_from_token(self, token: str) -> dict | None:
        from ..auth import decode_access_token
        payload = decode_access_token(token)
        user_id = payload.get("sub") if payload else None
        if not user_id:
            return None
        user = self.store.users.get(user_id)
        if user is None or user.get("status") != "ACTIVE":
            return None
        profile = self.store.profiles.get(user_id)
        return {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "student_no": profile.get("student_no") if profile else None,
            "major": profile.get("major") if profile else None,
            "grade": profile.get("grade") if profile else None,
        }
