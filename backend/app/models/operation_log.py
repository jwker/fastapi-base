"""SQLAlchemy 模型：操作审计日志。"""

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, BigIntPK


class OperationLog(Base):
    """操作审计日志：谁在何时对何资源做了什么写操作。

    字段设计对照若依 sys_oper_log：操作人/模块/动作/方法/路径/参数/IP/状态/时间。
    """

    __tablename__ = "operation_logs"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(BigIntPK, index=True, nullable=True)
    username: Mapped[str] = mapped_column(String(50), default="", index=True)
    module: Mapped[str] = mapped_column(String(50), default="未分类")
    action: Mapped[str] = mapped_column(String(20), default="other")
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    path: Mapped[str] = mapped_column(String(255), nullable=False)
    request_body: Mapped[str] = mapped_column(Text, default="")
    response_status: Mapped[int] = mapped_column(Integer, nullable=False)
    ip: Mapped[str] = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)
