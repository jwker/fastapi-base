"""模型统一导出，保证 Alembic autogenerate 与初始化脚本能发现全部表。"""

from app.models.announcement import Announcement
from app.models.associations import role_menus, role_permissions, user_roles
from app.models.config import SysConfig
from app.models.dict import DictItem, DictType
from app.models.file import File
from app.models.menu import Menu
from app.models.operation_log import OperationLog
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User

__all__ = [
    "User",
    "Role",
    "Permission",
    "Menu",
    "OperationLog",
    "File",
    "DictType",
    "DictItem",
    "SysConfig",
    "Announcement",
    "user_roles",
    "role_permissions",
    "role_menus",
]
