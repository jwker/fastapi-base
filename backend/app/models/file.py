"""SQLAlchemy 模型：上传文件元数据（素材库）。"""

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, BigIntPK


class File(Base):
    """上传文件元数据：二进制在磁盘 /uploads，表里只记引用信息。

    source（来源，程序自动打标）：avatar=头像消费端 / manual=文件管理页手动传 / 未来 icon、banner 等
    remark（备注）：上传时可填的用途说明（如"首页轮播图"）。
    """

    __tablename__ = "files"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)  # 原始文件名
    url: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )  # /uploads/YYYYMM/UUID.ext
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)  # 字节数
    mime_type: Mapped[str] = mapped_column(String(50), default="")
    source: Mapped[str] = mapped_column(String(20), default="manual", index=True)
    remark: Mapped[str] = mapped_column(String(255), default="")
    created_by: Mapped[int | None] = mapped_column(BigIntPK, index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
