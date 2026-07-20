"""Authentication and user management service for database mode."""

from __future__ import annotations

import hashlib
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..config import get_settings
from ..contracts import Role
from ..models import StudentProfile, User
from ..utils import _utcnow


def hash_password(password: str) -> str:
    from passlib.context import CryptContext

    return CryptContext(schemes=["bcrypt"], deprecated="auto").hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    if password_hash.startswith("sha256$"):
        expected = password_hash.split("$", 1)[1]
        actual = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return actual == expected
    from passlib.context import CryptContext

    return CryptContext(schemes=["bcrypt"], deprecated="auto").verify(password, password_hash)


def create_access_token(user_id: str, role: str) -> str:
    from jose import jwt

    settings = get_settings()
    payload = {
        "sub": user_id,
        "role": role,
        "exp": _utcnow() + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict | None:
    from jose import JWTError, jwt

    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return None


async def authenticate(session: AsyncSession, username: str, password: str) -> dict | None:
    user = (
        await session.execute(
            select(User).options(selectinload(User.student_profile)).where(User.username == username)
        )
    ).scalar_one_or_none()
    if user is None or user.status != "ACTIVE" or not verify_password(password, user.password_hash):
        return None
    profile = user.student_profile
    return {
        "access_token": create_access_token(user.id, user.role),
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "student_no": profile.student_no if profile else None,
            "major": profile.major if profile else None,
            "grade": profile.grade if profile else None,
        },
    }


async def register_student(
    session: AsyncSession,
    *,
    username: str,
    password: str,
    student_no: str,
    major: str = "",
    grade: int = 1,
) -> dict:
    existing_username = (
        await session.execute(select(User).where(func.lower(User.username) == username.casefold()))
    ).scalar_one_or_none()
    if existing_username is not None:
        raise ValueError("USERNAME_EXISTS")
    existing_student_no = (
        await session.execute(select(StudentProfile).where(StudentProfile.student_no == student_no))
    ).scalar_one_or_none()
    if existing_student_no is not None:
        raise ValueError("STUDENT_NO_EXISTS")

    user = User(username=username, password_hash=hash_password(password), role=Role.STUDENT.value, status="ACTIVE")
    session.add(user)
    await session.flush()
    session.add(StudentProfile(user_id=user.id, student_no=student_no, major=major, grade=grade))
    await session.flush()
    return {
        "access_token": create_access_token(user.id, user.role),
        "token_type": "bearer",
        "user": {"id": user.id, "username": user.username, "role": user.role, "student_no": student_no, "major": major, "grade": grade},
    }


async def get_user_from_token(session: AsyncSession, token: str) -> dict | None:
    payload = decode_access_token(token)
    user_id = payload.get("sub") if payload else None
    if not user_id:
        return None
    user = (
        await session.execute(
            select(User).options(selectinload(User.student_profile)).where(User.id == user_id)
        )
    ).scalar_one_or_none()
    if user is None or user.status != "ACTIVE":
        return None
    profile = user.student_profile
    return {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "student_no": profile.student_no if profile else None,
        "major": profile.major if profile else None,
        "grade": profile.grade if profile else None,
    }
