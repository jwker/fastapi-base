"""模型统一导出，保证 Alembic autogenerate 与初始化脚本能发现全部表。"""

from app.models.associations import role_menus, role_permissions, user_roles
from app.models.menu import Menu
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User

__all__ = ["User", "Role", "Permission", "Menu", "user_roles", "role_permissions", "role_menus"]
