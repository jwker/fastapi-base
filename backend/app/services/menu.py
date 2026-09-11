"""菜单服务（树形结构）。"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.response import AppError
from app.models.menu import Menu
from app.models.user import User


def build_tree(menus: list[Menu]) -> list[Menu]:
    """按 parent_id 组装层级树。

    注意：查询已用 selectinload 填充 children，这里需先重置集合，
    否则会在已加载的 children 上重复追加导致重复。
    """
    by_id = {m.id: m for m in menus}
    for m in menus:
        m.children = []
    roots: list[Menu] = []
    for m in menus:
        if m.parent_id and m.parent_id in by_id:
            by_id[m.parent_id].children.append(m)
        else:
            roots.append(m)
    return roots


def _query():
    return (
        select(Menu)
        .options(selectinload(Menu.children))
        .order_by(Menu.sort_order.asc(), Menu.id.asc())
    )


async def list_menus(db: AsyncSession) -> list[Menu]:
    rows = (await db.execute(_query())).scalars().all()
    return build_tree(list(rows))


async def list_user_menus(db: AsyncSession, user: User) -> list[Menu]:
    """当前用户可访问的菜单树。

    规则（主流 RBAC）：
    - 超管：全部菜单
    - 普通用户：菜单 = 该用户角色分配的菜单（role_menus），
      角色未分配菜单则看不到任何菜单（权限码只做按钮/接口校验，不参与菜单显示）。
    - 父级菜单若无任何可见子菜单（容器为空），整体隐藏，避免出现空下拉。
    """
    if user.is_superuser:
        return await list_menus(db)

    # 角色分配的菜单 id 集合（user.roles 与 role.menus 均已 selectin 加载）
    assigned_ids = {m.id for role in user.roles for m in role.menus}
    if not assigned_ids:
        return []

    all_rows = (await db.execute(_query())).scalars().all()
    visible_ids = {m.id for m in all_rows if m.id in assigned_ids}

    # 补全不可见菜单的祖先链，保证树结构完整（父级作为容器保留）
    by_id = {m.id: m for m in all_rows}
    for m in all_rows:
        pid = m.parent_id
        while pid and pid not in visible_ids:
            visible_ids.add(pid)
            pid = by_id[pid].parent_id if pid in by_id else None

    kept = [m for m in all_rows if m.id in visible_ids]
    tree = build_tree(kept)

    # 剪除空容器：数据库中作为父级存在、但过滤后无可见子菜单的节点 → 隐藏
    container_ids = {m.parent_id for m in all_rows if m.parent_id}

    def prune(nodes: list[Menu]) -> list[Menu]:
        out: list[Menu] = []
        for m in nodes:
            m.children = prune(m.children)
            if m.id in container_ids and not m.children:
                continue
            out.append(m)
        return out

    return prune(tree)


async def get_menu(db: AsyncSession, menu_id: int) -> Menu:
    menu = await db.get(Menu, menu_id)
    if not menu:
        raise AppError(404, "菜单不存在")
    return menu


async def create_menu(db: AsyncSession, data: dict) -> Menu:
    if data.get("parent_id"):
        await get_menu(db, data["parent_id"])
    menu = Menu(**data)
    db.add(menu)
    await db.commit()
    await db.refresh(menu)
    return menu


async def update_menu(db: AsyncSession, menu_id: int, data: dict) -> Menu:
    menu = await get_menu(db, menu_id)
    if data.get("parent_id") == menu_id:
        raise AppError(400, "父菜单不能是自己")
    if data.get("parent_id"):
        await get_menu(db, data["parent_id"])
    for key, value in data.items():
        if value is None and key != "permission_code":
            continue
        setattr(menu, key, value)
    await db.commit()
    await db.refresh(menu)
    return menu


async def delete_menu(db: AsyncSession, menu_id: int) -> None:
    menu = await get_menu(db, menu_id)
    await db.delete(menu)
    await db.commit()
