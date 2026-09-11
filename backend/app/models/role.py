"""SQLAlchemy 模型：角色。"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, BigIntPK

from .associations import role_menus, role_permissions, user_roles


class Role(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[int] = mapped_column(Integer, default=1, comment="1启用 0禁用")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    users: Mapped[list["User"]] = relationship(  # noqa: F821
        secondary=user_roles, back_populates="roles"
    )
    permissions: Mapped[list["Permission"]] = relationship(  # noqa: F821
        secondary=role_permissions, back_populates="roles", lazy="selectin"
    )
    menus: Mapped[list["Menu"]] = relationship(  # noqa: F821
        secondary=role_menus, back_populates="roles", lazy="selectin"
    )
