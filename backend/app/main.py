import os

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import get_current_user
from .config import get_settings
from .routers import admin, auth, courses, student

app = FastAPI(
    title="AI 课程选课冲突与候补调整系统",
    version="0.1.0-baseline",
    description="第一步并行开发基线：契约优先、内存数据、可替换实现。",
)

local_frontend_origins = {
    'http://localhost:5173',
    'http://localhost:5174',
    'http://127.0.0.1:5173',
    'http://127.0.0.1:5174',
    os.getenv('STUDENT_WEB_ORIGIN', '').strip(),
    os.getenv('ADMIN_WEB_ORIGIN', '').strip(),
}
local_frontend_origins.discard('')

app.add_middleware(
    CORSMiddleware,
    allow_origins=sorted(local_frontend_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health", tags=["system"])
async def health() -> dict:
    settings = get_settings()
    database = None
    if settings.database_enabled:
        from .database import database_health

        database = await database_health()
    return {
        "data": {
            "status": "ok" if database is not False else "degraded",
            "baseline": not settings.database_enabled,
            "storage": "mysql" if settings.database_enabled else "memory",
            "database": database,
        },
        "meta": {"request_id": "health"},
    }


@app.get("/api/v1/me", tags=["auth"])
async def me(user: dict = Depends(get_current_user)):
    return {"data": user, "meta": {"request_id": "me"}}


app.include_router(auth.router)
app.include_router(courses.router)
app.include_router(student.router)
app.include_router(admin.router)
