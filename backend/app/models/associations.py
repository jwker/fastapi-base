"""多对多关联表。"""

from sqlalchemy import Column, ForeignKey, Table

from app.core.database import Base, BigIntPK

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", BigIntPK, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", BigIntPK, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", BigIntPK, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column(
        "permission_id",
        BigIntPK,
        ForeignKey("permissions.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

role_menus = Table(
    "role_menus",
    Base.metadata,
    Column("role_id", BigIntPK, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("menu_id", BigIntPK, ForeignKey("menus.id", ondelete="CASCADE"), primary_key=True),
)
