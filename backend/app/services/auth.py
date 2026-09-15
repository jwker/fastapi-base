"""认证服务：登录、刷新、登出。"""

from datetime import datetime, timedelta

import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import (
    create_access_token,
    create_refresh_token,
    revoke_refresh_token,
    rotate_refresh_token,
    store_refresh_token,
)
from app.core.config import settings
from app.core.response import AppError
from app.core.security import hash_password, verify_password
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

    user = await db.get(User, user_id)
    if not user or user.status != 1:
        raise AppError(401, "账号不可用")

    access = create_access_token(user.id)
    refresh = create_refresh_token(user.id)
    # 原子轮换（CAS）：仅当 Redis 中仍是旧 token 才写入新 token。
    # 并发 refresh 场景只有第一个能成功，杜绝"多个新 token 同时返回、仅一个有效"的分叉。
    rotated = await rotate_refresh_token(
        user_id,
        refresh_token,
        refresh,
        int(timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS).total_seconds()),
    )
    if not rotated:
        raise AppError(401, "刷新凭证已失效，请重新登录")
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


async def change_password(
    db: AsyncSession, user: User, old_password: str, new_password: str
) -> None:
    """修改密码：校验旧密码后更新哈希。"""
    if not verify_password(old_password, user.password_hash):
        raise AppError(400, "原密码错误")
    if old_password == new_password:
        raise AppError(400, "新密码不能与原密码相同")
    user.password_hash = hash_password(new_password)
    await db.commit()


async def update_profile(db: AsyncSession, user: User, data: dict) -> User:
    """更新个人资料：仅 nickname/email/phone/avatar（白名单在 schema 层已限定）。"""
    for key, value in data.items():
        if value is None:
            continue
        setattr(user, key, value)
    await db.commit()
    await db.refresh(user)
    return user
