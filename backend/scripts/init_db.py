"""数据初始化：权限 → 角色 → 超管 → 菜单。幂等，可重复执行。

用法：uv run python scripts/init_db.py
"""

import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.menu import Menu
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User

# 核心权限：{resource}:{action}
PERMISSIONS: list[dict] = [
    # 用户
    {"name": "用户查询", "code": "user:read", "resource": "user", "action": "read"},
    {"name": "用户创建", "code": "user:create", "resource": "user", "action": "create"},
    {"name": "用户编辑", "code": "user:update", "resource": "user", "action": "update"},
    {"name": "用户删除", "code": "user:delete", "resource": "user", "action": "delete"},
    # 角色
    {"name": "角色查询", "code": "role:read", "resource": "role", "action": "read"},
    {"name": "角色创建", "code": "role:create", "resource": "role", "action": "create"},
    {"name": "角色编辑", "code": "role:update", "resource": "role", "action": "update"},
    {"name": "角色删除", "code": "role:delete", "resource": "role", "action": "delete"},
    # 菜单
    {"name": "菜单查询", "code": "menu:read", "resource": "menu", "action": "read"},
    {"name": "菜单创建", "code": "menu:create", "resource": "menu", "action": "create"},
    {"name": "菜单编辑", "code": "menu:update", "resource": "menu", "action": "update"},
    {"name": "菜单删除", "code": "menu:delete", "resource": "menu", "action": "delete"},
    # 权限
    {"name": "权限查询", "code": "permission:read", "resource": "permission", "action": "read"},
    {"name": "权限分配", "code": "permission:assign", "resource": "permission", "action": "assign"},
    # 审计日志
    {"name": "操作日志查询", "code": "audit:read", "resource": "audit", "action": "read"},
    {"name": "操作日志删除", "code": "audit:delete", "resource": "audit", "action": "delete"},
]

# 角色：code -> (名称, 描述, 权限码集合)
ROLES: dict[str, tuple[str, str, list[str]]] = {
    "super_admin": ("超级管理员", "拥有全部权限", []),  # is_superuser 标志，跳过校验
    "admin": (
        "管理员",
        "管理用户/角色/菜单，可分配权限",
        [
            "user:create",
            "user:read",
            "user:update",
            "user:delete",
            "role:create",
            "role:read",
            "role:update",
            "role:delete",
            "menu:create",
            "menu:read",
            "menu:update",
            "menu:delete",
            "permission:read",
            "permission:assign",
            "audit:read",
            "audit:delete",
        ],
    ),
    "user": (
        "普通用户",
        "只读",
        ["user:read", "role:read", "menu:read", "permission:read"],
    ),
}

# 菜单树：(name, path, component, icon, permission_code, [children])
MENUS: list[dict] = [
    {
        "name": "仪表盘",
        "path": "/dashboard",
        "component": "Dashboard",
        "icon": "Odometer",
        "permission_code": None,
        "children": [],
    },
    {
        "name": "系统管理",
        "path": "/system",
        "component": "Layout",
        "icon": "Setting",
        "permission_code": None,
        "children": [
            {
                "name": "用户管理",
                "path": "/users",
                "component": "UserList",
                "icon": "User",
                "permission_code": "user:read",
                "children": [],
            },
            {
                "name": "角色管理",
                "path": "/roles",
                "component": "RoleList",
                "icon": "Avatar",
                "permission_code": "role:read",
                "children": [],
            },
            {
                "name": "权限管理",
                "path": "/permissions",
                "component": "PermissionList",
                "icon": "Lock",
                "permission_code": "permission:read",
                "children": [],
            },
            {
                "name": "菜单管理",
                "path": "/menus",
                "component": "MenuList",
                "icon": "Menu",
                "permission_code": "menu:read",
                "children": [],
            },
            {
                "name": "操作日志",
                "path": "/audit-logs",
                "component": "AuditLogList",
                "icon": "Document",
                "permission_code": "audit:read",
                "children": [],
            },
        ],
    },
]


async def init_permissions(db) -> dict[str, int]:
    """返回 code -> id 映射。"""
    mapping: dict[str, int] = {}
    for item in PERMISSIONS:
        exists = (
            await db.execute(select(Permission).where(Permission.code == item["code"]))
        ).scalar_one_or_none()
        if not exists:
            exists = Permission(**item)
            db.add(exists)
            await db.flush()
        mapping[item["code"]] = exists.id
    return mapping


async def init_roles(db, perm_mapping: dict[str, int]) -> dict[str, Role]:
    roles: dict[str, Role] = {}
    for code, (name, desc, perm_codes) in ROLES.items():
        role = (await db.execute(select(Role).where(Role.code == code))).scalar_one_or_none()
        if not role:
            role = Role(name=name, code=code, description=desc)
            db.add(role)  # 保持 pending，集合赋值不触发 IO；无需 id
        if perm_codes:
            perms = (
                (await db.execute(select(Permission).where(Permission.code.in_(perm_codes))))
                .scalars()
                .all()
            )
            role.permissions = list(perms)
        roles[code] = role
    return roles


async def init_superuser(db, super_admin_role: Role) -> None:
    username = settings.INIT_ADMIN_USERNAME
    user = (await db.execute(select(User).where(User.username == username))).scalar_one_or_none()
    if not user:
        user = User(
            username=username,
            password_hash=hash_password(settings.INIT_ADMIN_PASSWORD),
            nickname="超级管理员",
            is_superuser=True,
        )
        user.roles = [super_admin_role]
        db.add(user)


async def init_menus(db, roles: dict[str, Role]) -> None:
    """插入菜单并同步角色菜单分配。

    - 菜单插入幂等 + **增量补缺**：按 (path, parent_id) 逐条查找，缺的补插
      （旧实现"表空才建"导致已有库新增菜单不生效）
    - 角色分配每次执行都同步：admin、user 角色分配全部菜单（主流 RBAC：
      菜单显示 = 角色分配，权限码只做按钮/接口校验）
    """
    from sqlalchemy.orm import selectinload

    async def sync(items: list[dict], parent_id: int | None = None) -> None:
        for item in items:
            menu = (
                await db.execute(
                    select(Menu).where(Menu.path == item["path"], Menu.parent_id == parent_id)
                )
            ).scalar_one_or_none()
            if menu is None:
                menu = Menu(
                    name=item["name"],
                    path=item["path"],
                    component=item.get("component", ""),
                    icon=item.get("icon", ""),
                    permission_code=item.get("permission_code"),
                    parent_id=parent_id,
                )
                db.add(menu)
                await db.flush()  # 立即拿 id 供子菜单关联
            await sync(item.get("children", []), menu.id)

    await sync(MENUS)

    all_menus = (await db.execute(select(Menu))).scalars().all()
    for code in ("admin", "user"):
        role = roles.get(code)
        if not role:
            continue
        # 重新查询并加载 menus 集合，避免对 persistent 对象集合赋值触发 lazy IO
        loaded = (
            await db.execute(
                select(Role).where(Role.id == role.id).options(selectinload(Role.menus))
            )
        ).scalar_one()
        loaded.menus = list(all_menus)


async def main() -> None:
    async with AsyncSessionLocal() as db:
        # 关闭隐式 autoflush：查询时不要把 pending 角色 flush 成 persistent，
        # 否则后续集合赋值（role.permissions = ...）会触发未加载集合的 lazy IO。
        with db.no_autoflush:
            perm_mapping = await init_permissions(db)
            roles = await init_roles(db, perm_mapping)
            await init_superuser(db, roles["super_admin"])
            await init_menus(db, roles)
        await db.commit()
        print(
            f"初始化完成：权限 {len(PERMISSIONS)} 个，角色 {len(ROLES)} 个，"
            f"超管 {settings.INIT_ADMIN_USERNAME}/{settings.INIT_ADMIN_PASSWORD}"
        )


if __name__ == "__main__":
    asyncio.run(main())
