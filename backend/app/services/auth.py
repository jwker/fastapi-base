"""认证服务：登录、刷新、登出。"""

from datetime import datetime

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    create_access_token,
    create_refresh_token,
    revoke_refresh_token,
    store_refresh_token,
    verify_refresh_token,
)
from app.core.config import settings
from app.core.response import AppError
from app.core.security import verify_password
from app.models.user import User


async def authenticate(db: AsyncSession, username: str, password: str) -> tuple[User, str, str]:
    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        raise AppError(400, "用户名或密码错误")
    if user.status != 1:
        raise AppError(403, "账号已被禁用")

    user.last_login_at = datetime.now()
    await db.commit()

    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    await store_refresh_token(user.id, refresh)
    return user, access, refresh


def _decode_refresh(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.PyJWTError:
        raise AppError(401, "无效的刷新凭证") from None
    if payload.get("type") != "refresh":
        raise AppError(401, "无效的刷新凭证")
    return payload


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> tuple[str, str]:
    payload = _decode_refresh(refresh_token)
    user_id = int(payload["sub"])
    if not await verify_refresh_token(user_id, refresh_token):
        raise AppError(401, "刷新凭证已失效，请重新登录")

    user = await db.get(User, user_id)
    if not user or user.status != 1:
        raise AppError(401, "账号不可用")

    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    await store_refresh_token(user.id, refresh)
    return access, refresh


async def logout(user_id: int, refresh_token: str | None) -> None:
    if refresh_token:
        try:
            payload = _decode_refresh(refresh_token)
            if int(payload["sub"]) == user_id:
                await revoke_refresh_token(user_id)
        except AppError:
            pass
    else:
        await revoke_refresh_token(user_id)
