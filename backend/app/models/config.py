"""SQLAlchemy 模型：系统参数配置（sys_config）。

参照若依 sys_config 表结构：key 全局唯一，value 统一存字符串，
value_type 仅标注类型（string/int/bool），由调用方自行转换。
"""

from datetime import datetime

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base, BigIntPK


class SysConfig(Base):
    __tablename__ = "sys_configs"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False, comment="配置键，如 site_name"
    )
    value: Mapped[str] = mapped_column(Text, nullable=False, comment="配置值（统一字符串）")
    value_type: Mapped[str] = mapped_column(
        String(20), default="string", comment="值类型标注：string/int/bool"
    )
    remark: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )
