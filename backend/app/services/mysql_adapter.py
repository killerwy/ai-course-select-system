"""Optional MySQL session boundary for the C admin services.

The project baseline intentionally does not install database drivers in the
offline development environment.  This module keeps the production URL and
session factory in one place so A's SQLAlchemy repository can be plugged into
the existing ``AdminRepository`` protocol without changing admin routes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class MySQLDependencyError(RuntimeError):
    code = "MYSQL_DEPENDENCY_MISSING"


@dataclass(frozen=True)
class MySQLSettings:
    database_url: str
    pool_pre_ping: bool = True
    pool_recycle: int = 1800

    def validate(self) -> None:
        if not self.database_url.startswith("mysql+aiomysql://"):
            raise ValueError("MYSQL_URL_INVALID")


def dependency_status() -> dict[str, bool]:
    try:
        import sqlalchemy  # noqa: F401
    except ModuleNotFoundError:
        sqlalchemy_available = False
    else:
        sqlalchemy_available = True
    try:
        import aiomysql  # noqa: F401
    except ModuleNotFoundError:
        aiomysql_available = False
    else:
        aiomysql_available = True
    return {"sqlalchemy": sqlalchemy_available, "aiomysql": aiomysql_available}


def build_async_session_factory(settings: MySQLSettings) -> Any:
    """Create an async SQLAlchemy session factory when optional deps exist."""

    settings.validate()
    status = dependency_status()
    if not all(status.values()):
        raise MySQLDependencyError(
            f"{MySQLDependencyError.code}: install backend/requirements-mysql.txt before enabling MySQL"
        )
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine(
        settings.database_url,
        pool_pre_ping=settings.pool_pre_ping,
        pool_recycle=settings.pool_recycle,
    )
    return async_sessionmaker(engine, expire_on_commit=False)

