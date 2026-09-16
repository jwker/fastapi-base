"""数据初始化：权限 → 角色 → 超管 → 菜单。幂等，可重复执行。

用法：uv run python scripts/init_db.py
"""

import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.config import SysConfig
from app.models.dict import DictItem, DictType
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
    # 文件管理
    {"name": "文件查询", "code": "file:read", "resource": "file", "action": "read"},
    {"name": "文件删除", "code": "file:delete", "resource": "file", "action": "delete"},
    # 数据字典
    {"name": "字典查询", "code": "dict:read", "resource": "dict", "action": "read"},
    {"name": "字典维护", "code": "dict:write", "resource": "dict", "action": "write"},
    # 系统参数
    {"name": "参数查询", "code": "config:read", "resource": "config", "action": "read"},
    {"name": "参数维护", "code": "config:write", "resource": "config", "action": "write"},
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
            "file:read",
            "file:delete",
            "dict:read",
            "dict:write",
            "config:read",
            "config:write",
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
            {
                "name": "字典管理",
                "path": "/dicts",
                "component": "DictList",
                "icon": "Collection",
                "permission_code": "dict:read",
                "children": [],
            },
            {
                "name": "参数设置",
                "path": "/configs",
                "component": "ConfigList",
                "icon": "Tools",
                "permission_code": "config:read",
                "children": [],
            },
        ],
    },
    {
        "name": "文件管理",
        "path": "/files",
        "component": "FileManager",
        "icon": "Folder",
        "permission_code": "file:read",
        "children": [],
    },
]

# 字典种子：type -> (名称, 备注, [(label, value, sort, is_default), ...])
# 系统参数示例（key, value, value_type, remark）
CONFIGS: list[tuple[str, str, str, str]] = [
    ("site_name", "FastAPI Base", "string", "站点名称，前端标题等处展示"),
    ("upload_max_size", "10", "int", "单文件上传大小上限（MB），业务侧校验"),
]

# 值与业务代码实际存储值对齐：
# sys_status -> User/Role.status(int)；file_source -> File.source；
# audit_action -> OperationLog.action（middleware/audit.py infer_action）。
DICTS: dict[str, tuple[str, str, list[tuple[str, str, int, bool]]]] = {
    "sys_status": (
        "系统状态",
        "用户/角色启用禁用状态（1=启用，0=禁用）",
        [
            ("启用", "1", 1, True),
            ("禁用", "0", 2, False),
        ],
    ),
    "file_source": (
        "文件来源",
        "文件上传来源打标（File.source）",
        [
            ("头像", "avatar", 1, False),
            ("素材", "manual", 2, True),
        ],
    ),
    "audit_action": (
        "审计动作",
        "操作日志动作类型（OperationLog.action）",
        [
            ("登录", "login", 1, False),
            ("登出", "logout", 2, False),
            ("新增", "create", 3, False),
            ("修改", "update", 4, False),
            ("删除", "delete", 5, False),
            ("其他", "other", 6, True),
        ],
    ),
}


async def init_configs(db) -> None:
    """系统参数示例，按 key 增量补缺（幂等，可重复执行；已存在的 key 不覆盖）。"""
    for key, value, value_type, remark in CONFIGS:
        exists = (
            await db.execute(select(SysConfig).where(SysConfig.key == key))
        ).scalar_one_or_none()
        if exists is None:
            db.add(SysConfig(key=key, value=value, value_type=value_type, remark=remark))


async def init_dicts(db) -> None:
    """字典类型 + 项，按 type 增量补缺（幂等，可重复执行）。"""
    for type_code, (name, remark, items) in DICTS.items():
        t = (
            await db.execute(select(DictType).where(DictType.type == type_code))
        ).scalar_one_or_none()
        if t is None:
            t = DictType(name=name, type=type_code, remark=remark)
            db.add(t)
            await db.flush()
        # 增量补项：已存在的 value 跳过，缺的补插
        existing_values = {
            i.value
            for i in (await db.execute(select(DictItem).where(DictItem.type_id == t.id))).scalars()
        }
        for label, value, sort, is_default in items:
            if value in existing_values:
                continue
            db.add(
                DictItem(
                    type_id=t.id,
                    label=label,
                    value=value,
                    sort=sort,
                    is_default=is_default,
                    status=1,
                )
            )


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
            await init_configs(db)
            await init_dicts(db)
        await db.commit()
        print(
            f"初始化完成：权限 {len(PERMISSIONS)} 个，角色 {len(ROLES)} 个，"
            f"配置 {len(CONFIGS)} 个，字典 {len(DICTS)} 个，超管 "
            f"{settings.INIT_ADMIN_USERNAME}/{settings.INIT_ADMIN_PASSWORD}"
        )


if __name__ == "__main__":
    asyncio.run(main())
