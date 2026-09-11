"""SQLAlchemy 模型：权限。"""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, BigIntPK

from .associations import role_permissions


class Permission(Base):
    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    resource: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    roles: Mapped[list["Role"]] = relationship(  # noqa: F821
        secondary=role_permissions, back_populates="permissions"
    )
