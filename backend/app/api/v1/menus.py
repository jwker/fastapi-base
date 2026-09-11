"""菜单管理 API。"""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.response import success
from app.schemas.menu import MenuCreate, MenuOut, MenuUpdate
from app.services import menu as menu_service

router = APIRouter(prefix="/menus", tags=["菜单管理"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


def _to_out(menu) -> MenuOut:
    return MenuOut(
        id=menu.id,
        parent_id=menu.parent_id,
        name=menu.name,
        path=menu.path,
        component=menu.component,
        icon=menu.icon,
        sort_order=menu.sort_order,
        is_visible=menu.is_visible,
        permission_code=menu.permission_code,
        created_at=menu.created_at,
        children=[_to_out(c) for c in menu.children],
    )


@router.get("/tree")
async def get_menu_tree(
    db: DbDep, _: Annotated[CurrentUser, Depends(require_permission("menu:read"))]
):
    """完整菜单树（管理用，需 menu:read 权限）。"""
    tree = await menu_service.list_menus(db)
    return success([_to_out(m) for m in tree])


@router.get("/my")
async def get_my_menus(db: DbDep, user: CurrentUser):
    """当前用户可访问的菜单树（登录后前端动态路由用）。"""
    tree = await menu_service.list_user_menus(db, user)
    return success([_to_out(m) for m in tree])


@router.post("", status_code=201)
async def create_menu(
    data: MenuCreate,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("menu:create"))],
):
    menu = await menu_service.create_menu(db, data.model_dump())
    return success(_to_out(menu), "创建成功")


@router.put("/{menu_id}")
async def update_menu(
    menu_id: int,
    data: MenuUpdate,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("menu:update"))],
):
    menu = await menu_service.update_menu(db, menu_id, data.model_dump(exclude_unset=True))
    return success(_to_out(menu), "更新成功")


@router.delete("/{menu_id}")
async def delete_menu(
    menu_id: int,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("menu:delete"))],
):
    await menu_service.delete_menu(db, menu_id)
    return success(message="删除成功")
