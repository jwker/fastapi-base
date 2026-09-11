"""SQLAlchemy 模型：菜单（支持层级树）。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, BigIntPK

from .associations import role_menus


class Menu(Base):
    __tablename__ = "menus"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    parent_id: Mapped[int | None] = mapped_column(
        BigIntPK, ForeignKey("menus.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    path: Mapped[str] = mapped_column(String(100), nullable=False)
    component: Mapped[str] = mapped_column(String(100), default="")
    icon: Mapped[str] = mapped_column(String(50), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
    permission_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    children: Mapped[list["Menu"]] = relationship(
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Menu.sort_order",
    )
    parent: Mapped["Menu | None"] = relationship(back_populates="children", remote_side="Menu.id")

    roles: Mapped[list["Role"]] = relationship(  # noqa: F821
        secondary=role_menus, back_populates="menus"
    )
