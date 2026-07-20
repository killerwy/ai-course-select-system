"""FastAPI dependency that opens a transaction only in database mode."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

from .config import get_settings


async def get_optional_db() -> AsyncGenerator[Any | None, None]:
    if not get_settings().database_enabled:
        yield None
        return

    from .database import async_session_factory

    async with async_session_factory() as session:
        try:
            yield session
            if session.is_active:
                await session.commit()
            else:
                await session.rollback()
        except Exception:
            await session.rollback()
            raise
