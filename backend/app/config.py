"""Runtime configuration shared by the in-memory baseline and MySQL mode.

The application deliberately defaults to ``memory`` so the repository can be
started without infrastructure.  The Navicat/MySQL deployment is enabled with
``APP_STORAGE=mysql`` and ``DATABASE_URL`` (see ``backend/.env.example``).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def _load_local_env() -> None:
    """Load backend/.env when python-dotenv is available.

    No value is logged and an already exported environment variable always
    wins.  The file is optional, which keeps test and CI startup deterministic.
    """

    try:
        from dotenv import load_dotenv
    except ModuleNotFoundError:
        return
    load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)


_load_local_env()


@dataclass(frozen=True)
class Settings:
    app_storage: str
    database_url: str
    jwt_secret: str
    jwt_algorithm: str
    jwt_expire_minutes: int
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    student_web_origin: str
    admin_web_origin: str

    @property
    def database_enabled(self) -> bool:
        return self.app_storage.lower() in {"mysql", "database"}


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    storage = os.getenv("APP_STORAGE", "memory").strip().lower()
    if storage not in {"memory", "mysql", "database"}:
        raise ValueError("APP_STORAGE must be memory or mysql")
    return Settings(
        app_storage=storage,
        database_url=os.getenv(
            "DATABASE_URL",
            "mysql+aiomysql://root:password@127.0.0.1:3306/course_selection?charset=utf8mb4",
        ),
        jwt_secret=os.getenv("JWT_SECRET", "dev-secret-change-before-deployment"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        jwt_expire_minutes=int(os.getenv("JWT_EXPIRE_MINUTES", "480")),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
        deepseek_base_url=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        deepseek_model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        student_web_origin=os.getenv("STUDENT_WEB_ORIGIN", "http://127.0.0.1:5173"),
        admin_web_origin=os.getenv("ADMIN_WEB_ORIGIN", "http://127.0.0.1:5174"),
    )
