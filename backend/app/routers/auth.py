from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException

from ..contracts import LoginRequest, LoginResponse, RegisterRequest
from ..store import STORE
from ..storage import get_optional_db

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=LoginResponse, status_code=201)
async def register(payload: RegisterRequest, db=Depends(get_optional_db)) -> LoginResponse:
    """Register a student and immediately return a student session."""

    username = payload.username.strip()
    student_no = payload.student_no.strip()
    if not username or not student_no:
        raise HTTPException(status_code=422, detail="用户名和学号不能为空")

    if db is not None:
        from ..services.database_store import register_student

        try:
            result = await register_student(
                db,
                username=username,
                password=payload.password,
                student_no=student_no,
                major=payload.major.strip(),
                grade=payload.grade,
            )
        except ValueError as exc:
            code = str(exc)
            if code == "USERNAME_EXISTS":
                raise HTTPException(status_code=409, detail="用户名已存在，请更换后再注册") from exc
            if code == "STUDENT_NO_EXISTS":
                raise HTTPException(status_code=409, detail="学号已注册，请直接登录或更换学号") from exc
            raise HTTPException(status_code=422, detail="注册信息不合法") from exc
        return LoginResponse(**result)

    if any(item.get("username", "").casefold() == username.casefold() for item in STORE.users.values()):
        raise HTTPException(status_code=409, detail="用户名已存在，请更换后再注册")
    if any(item.get("student_no") == student_no for item in STORE.users.values()):
        raise HTTPException(status_code=409, detail="学号已注册，请直接登录或更换学号")
    user_id = f"student-{uuid4().hex[:12]}"
    user = {
        "id": user_id,
        "username": username,
        "password": payload.password,
        "role": "STUDENT",
        "student_no": student_no,
        "major": payload.major.strip(),
        "grade": payload.grade,
    }
    STORE.users[user_id] = user
    token = f"demo-token-{user_id}"
    STORE.tokens[token] = user_id
    return LoginResponse(access_token=token, user={key: value for key, value in user.items() if key != "password"})


@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest, db=Depends(get_optional_db)) -> LoginResponse:
    if db is not None:
        from ..services.database_store import authenticate

        result = await authenticate(db, payload.username, payload.password)
        if result is None:
            raise HTTPException(status_code=401, detail="用户名或密码错误")
        return LoginResponse(**result)
    user = next(
        (item for item in STORE.users.values() if item["username"] == payload.username and item["password"] == payload.password),
        None,
    )
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = f"demo-token-{user['id']}"
    STORE.tokens[token] = user["id"]
    return LoginResponse(
        access_token=token,
        user={key: value for key, value in user.items() if key != "password"},
    )
