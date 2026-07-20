from typing import Callable

from fastapi import Depends, Header, HTTPException, status

from .contracts import Role
from .store import STORE
from .storage import get_optional_db


async def get_current_user(
    authorization: str | None = Header(default=None),
    db=Depends(get_optional_db),
) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少 Bearer Token")
    token = authorization.split(" ", 1)[1]
    if db is not None:
        from .services.database_store import get_user_from_token

        user = await get_user_from_token(db, token)
        if user is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 无效或用户不存在")
        return user
    user_id = STORE.tokens.get(token)
    if not user_id or user_id not in STORE.users:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token 无效或已过期")
    user = STORE.users[user_id]
    return {key: value for key, value in user.items() if key != "password"}


def require_role(*roles: Role) -> Callable:
    async def dependency(user: dict = Depends(get_current_user)) -> dict:
        if user["role"] not in {role.value for role in roles}:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="当前角色无权访问")
        return user

    return dependency
