"""角色服务。"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import AppError
from app.models.menu import Menu
from app.models.permission import Permission
from app.models.role import Role


async def list_roles(db: AsyncSession, page: int, page_size: int, keyword: str | None = None):
    stmt = select(Role)
    if keyword:
        stmt = stmt.where(Role.name.contains(keyword) | Role.code.contains(keyword))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        (
            await db.execute(
                stmt.order_by(Role.id.asc()).offset((page - 1) * page_size).limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return total, list(rows)


async def get_role(db: AsyncSession, role_id: int) -> Role:
    role = await db.get(Role, role_id)
    if not role:
        raise AppError(404, "角色不存在")
    return role


async def create_role(
    db: AsyncSession,
    name: str,
    code: str,
    description: str = "",
    status: int = 1,
    permission_ids: list[int] | None = None,
    menu_ids: list[int] | None = None,
) -> Role:
    exists = (await db.execute(select(Role.id).where(Role.code == code))).scalar_one_or_none()
    if exists:
        raise AppError(400, "角色编码已存在")
    role = Role(name=name, code=code, description=description, status=status)
    if permission_ids:
        role.permissions = list(
            (await db.execute(select(Permission).where(Permission.id.in_(permission_ids))))
            .scalars()
            .all()
        )
    if menu_ids:
        role.menus = list(
            (await db.execute(select(Menu).where(Menu.id.in_(menu_ids)))).scalars().all()
        )
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return role


async def update_role(
    db: AsyncSession,
    role_id: int,
    data: dict,
    permission_ids: list[int] | None = None,
    menu_ids: list[int] | None = None,
) -> Role:
    role = await get_role(db, role_id)
    for key, value in data.items():
        if value is None:
            continue
        setattr(role, key, value)
    if permission_ids is not None:
        role.permissions = list(
            (await db.execute(select(Permission).where(Permission.id.in_(permission_ids))))
            .scalars()
            .all()
        )
    if menu_ids is not None:
        role.menus = list(
            (await db.execute(select(Menu).where(Menu.id.in_(menu_ids)))).scalars().all()
        )
    await db.commit()
    await db.refresh(role)
    return role


async def delete_role(db: AsyncSession, role_id: int) -> None:
    role = await get_role(db, role_id)
    if role.code in ("super_admin", "admin", "user"):
        raise AppError(400, "内置角色不可删除")
    await db.delete(role)
    await db.commit()
