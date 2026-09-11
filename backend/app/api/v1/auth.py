"""认证 API。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import blacklist_access_token
from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.response import success
from app.schemas.auth import LoginRequest, LoginResponse, RefreshRequest, TokenPair, UserInfo
from app.services import auth as auth_service
from app.services.user import get_user_permission_codes, get_user_role_codes

router = APIRouter(prefix="/auth", tags=["认证"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


def _user_info(user) -> UserInfo:
    return UserInfo(
        id=user.id,
        username=user.username,
        nickname=user.nickname,
        email=user.email,
        avatar=user.avatar,
        is_superuser=user.is_superuser,
        permissions=get_user_permission_codes(user),
        roles=get_user_role_codes(user),
    )


@router.post("/login")
async def login(data: LoginRequest, db: DbDep):
    user, access, refresh = await auth_service.authenticate(db, data.username, data.password)
    return success(
        LoginResponse(
            tokens=TokenPair(access_token=access, refresh_token=refresh),
            user=_user_info(user),
        )
    )


@router.post("/refresh")
async def refresh(data: RefreshRequest, db: DbDep):
    access, refresh = await auth_service.refresh_tokens(db, data.refresh_token)
    return success(TokenPair(access_token=access, refresh_token=refresh))


@router.post("/logout")
async def logout(
    request: Request,
    user: CurrentUser,
    data: dict | None = None,
):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    await blacklist_access_token(token)
    refresh_token = (data or {}).get("refresh_token") if data else None
    await auth_service.logout(user.id, refresh_token)
    return success(message="已退出登录")


@router.get("/me")
async def me(user: CurrentUser):
    return success(_user_info(user))
