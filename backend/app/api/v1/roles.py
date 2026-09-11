"""角色管理 API。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.response import success
from app.schemas.role import RoleCreate, RoleOut, RolePage, RoleUpdate
from app.services import role as role_service

router = APIRouter(prefix="/roles", tags=["角色管理"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


def _to_out(role) -> RoleOut:
    return RoleOut(
        id=role.id,
        name=role.name,
        code=role.code,
        description=role.description,
        status=role.status,
        created_at=role.created_at,
        permission_ids=[p.id for p in role.permissions],
        menu_ids=[m.id for m in role.menus],
    )


@router.get("")
async def list_roles(
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("role:read"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    keyword: str | None = Query(None),
):
    total, rows = await role_service.list_roles(db, page, page_size, keyword)
    return success(RolePage(total=total, items=[_to_out(r) for r in rows]))


@router.get("/{role_id}")
async def get_role(
    role_id: int,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("role:read"))],
):
    role = await role_service.get_role(db, role_id)
    return success(_to_out(role))


@router.post("", status_code=201)
async def create_role(
    data: RoleCreate,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("role:create"))],
):
    role = await role_service.create_role(
        db, name=data.name, code=data.code, description=data.description, status=data.status
    )
    return success(_to_out(role), "创建成功")


@router.put("/{role_id}")
async def update_role(
    role_id: int,
    data: RoleUpdate,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("role:update"))],
):
    payload = data.model_dump(exclude_unset=True)
    role = await role_service.update_role(db, role_id, payload)
    return success(_to_out(role), "更新成功")


@router.put("/{role_id}/permissions")
async def assign_permissions(
    role_id: int,
    data: dict,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("role:update"))],
):
    permission_ids = data.get("permission_ids", [])
    role = await role_service.update_role(db, role_id, {}, permission_ids=permission_ids)
    return success(_to_out(role), "权限分配成功")


@router.put("/{role_id}/menus")
async def assign_menus(
    role_id: int,
    data: dict,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("role:update"))],
):
    menu_ids = data.get("menu_ids", [])
    role = await role_service.update_role(db, role_id, {}, menu_ids=menu_ids)
    return success(_to_out(role), "菜单分配成功")


@router.delete("/{role_id}")
async def delete_role(
    role_id: int,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("role:delete"))],
):
    await role_service.delete_role(db, role_id)
    return success(message="删除成功")
