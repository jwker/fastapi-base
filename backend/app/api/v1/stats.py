"""统计 API（仪表盘用）。"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser
from app.core.response import success
from app.models.menu import Menu
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User

router = APIRouter(prefix="/stats", tags=["统计"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@router.get("/overview")
async def overview(db: DbDep, _: CurrentUser):
    """仪表盘统计：用户/角色/权限/菜单数量。"""
    user_count = (await db.execute(select(func.count()).select_from(User))).scalar_one()
    role_count = (await db.execute(select(func.count()).select_from(Role))).scalar_one()
    permission_count = (await db.execute(select(func.count()).select_from(Permission))).scalar_one()
    menu_count = (await db.execute(select(func.count()).select_from(Menu))).scalar_one()
    return success(
        {
            "user_count": user_count,
            "role_count": role_count,
            "permission_count": permission_count,
            "menu_count": menu_count,
        }
    )
