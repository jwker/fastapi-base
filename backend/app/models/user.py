"""SQLAlchemy 模型：用户。"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, BigIntPK

from .associations import user_roles


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    nickname: Mapped[str] = mapped_column(String(50), default="")
    email: Mapped[str] = mapped_column(String(100), default="")
    phone: Mapped[str] = mapped_column(String(20), default="")
    avatar: Mapped[str] = mapped_column(String(255), default="")
    status: Mapped[int] = mapped_column(default=1, comment="1启用 0禁用")
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    roles: Mapped[list["Role"]] = relationship(  # noqa: F821
        secondary=user_roles, back_populates="users", lazy="selectin"
    )
