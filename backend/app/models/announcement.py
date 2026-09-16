"""SQLAlchemy 模型：通知公告（sys_announcement）。

管理端发布/编辑/下架/删除；用户端仅看已发布且未过期的。
status：0 草稿 / 1 已发布 / 2 已下线；is_top 置顶优先；expire_time 空 = 永不过期。
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, BigIntPK


class Announcement(Base):
    __tablename__ = "sys_announcements"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False, comment="标题")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="正文（纯文本）")
    type: Mapped[str] = mapped_column(
        String(20),
        default="notice",
        comment="类型：notice=通知 / announcement=公告（字典 sys_announce_type）",
    )
    status: Mapped[int] = mapped_column(
        Integer, default=0, index=True, comment="状态：0 草稿 / 1 已发布 / 2 已下线"
    )
    is_top: Mapped[bool] = mapped_column(
        Boolean, default=False, index=True, comment="是否置顶（置顶优先展示）"
    )
    expire_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, comment="过期时间，空 = 永不过期"
    )
    publish_time: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True, index=True, comment="发布时间（发布动作时写入）"
    )
    created_by: Mapped[int | None] = mapped_column(
        BigIntPK, ForeignKey("users.id"), nullable=True, comment="发布人"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
