"""FastAPI 依赖：当前用户、权限校验（RBAC）。"""

from typing import Annotated

import jwt
from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import decode_token
from app.core.database import get_db
from app.core.response import AppError
from app.models.user import User

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def get_current_user(request: Request, db: DbDep) -> User:
    """从 Authorization 头解析 Access Token 并加载用户。"""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise AppError(401, "未登录或凭证缺失")
    token = auth.removeprefix("Bearer ").strip()
    try:
        payload = await decode_token(token)
    except jwt.ExpiredSignatureError:
        raise AppError(401, "登录已过期") from None
    except jwt.PyJWTError:
        raise AppError(401, "无效的凭证") from None

    if payload.get("type") != "access":
        raise AppError(401, "无效的凭证")

    user = await db.get(User, int(payload["sub"]))
    if not user:
        raise AppError(401, "用户不存在")
    if user.status != 1:
        raise AppError(403, "账号已被禁用")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_user_permissions(user: User) -> set[str]:
    """汇总用户权限码。超管返回通配。"""
    if user.is_superuser:
        return {"*"}
    perms: set[str] = set()
    for role in user.roles:
        if role.status == 1:
            perms.update(p.code for p in role.permissions)
    return perms


def require_permission(permission_code: str):
    """权限校验依赖工厂：require_permission("user:create")。"""

    async def checker(user: CurrentUser) -> User:
        perms = get_user_permissions(user)
        if "*" in perms or permission_code in perms:
            return user
        raise AppError(403, f"缺少权限: {permission_code}")

    return checker
