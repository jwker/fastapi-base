"""用户管理 API。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.response import success
from app.schemas.user import UserCreate, UserOut, UserPage, UserUpdate
from app.services import user as user_service

router = APIRouter(prefix="/users", tags=["用户管理"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


def _to_out(user) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        nickname=user.nickname,
        email=user.email,
        phone=user.phone,
        status=user.status,
        is_superuser=user.is_superuser,
        last_login_at=user.last_login_at,
        created_at=user.created_at,
        role_ids=[r.id for r in user.roles],
    )


@router.get("")
async def list_users(
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("user:read"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    keyword: str | None = Query(None),
):
    total, rows = await user_service.list_users(db, page, page_size, keyword)
    return success(UserPage(total=total, items=[_to_out(u) for u in rows]))


@router.get("/{user_id}")
async def get_user(
    user_id: int,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("user:read"))],
):
    user = await user_service.get_user(db, user_id)
    return success(_to_out(user))


@router.post("", status_code=201)
async def create_user(
    data: UserCreate,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("user:create"))],
):
    user = await user_service.create_user(
        db,
        username=data.username,
        password=data.password,
        nickname=data.nickname,
        email=str(data.email) if data.email else "",
        phone=data.phone,
        status=data.status,
        role_ids=data.role_ids,
    )
    return success(_to_out(user), "创建成功")


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    data: UserUpdate,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("user:update"))],
):
    payload = data.model_dump(exclude_unset=True)
    role_ids = payload.pop("role_ids", None)
    user = await user_service.update_user(db, user_id, payload, role_ids)
    return success(_to_out(user), "更新成功")


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("user:delete"))],
):
    await user_service.delete_user(db, user_id)
    return success(message="删除成功")
