"""权限管理 API（只读 + 分配）。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.response import success
from app.models.permission import Permission
from app.schemas.permission import PermissionOut, PermissionPage

router = APIRouter(prefix="/permissions", tags=["权限管理"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("")
async def list_permissions(
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("permission:read"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=200),
    keyword: str | None = Query(None),
):
    stmt = select(Permission)
    if keyword:
        stmt = stmt.where(
            Permission.code.contains(keyword)
            | Permission.name.contains(keyword)
            | Permission.resource.contains(keyword)
        )
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        (
            await db.execute(
                stmt.order_by(Permission.resource.asc(), Permission.action.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return success(
        PermissionPage(
            total=total,
            items=[PermissionOut.model_validate(p) for p in rows],
        )
    )
