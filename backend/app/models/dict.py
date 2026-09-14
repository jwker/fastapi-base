"""SQLAlchemy 模型：数据字典（字典类型 + 字典项）。

参照若依 sys_dict_type / sys_dict_data 两表结构：
- DictType：字典类型（编码唯一，如 sys_status / file_source / audit_action）
- DictItem：字典项（label 显示文案 / value 存储值 / sort 排序 / is_default 默认）
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base, BigIntPK


class DictType(Base):
    __tablename__ = "dict_types"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), nullable=False, comment="字典名称")
    type: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False, comment="字典类型编码，如 file_source"
    )
    remark: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    items: Mapped[list["DictItem"]] = relationship(
        back_populates="dict_type", cascade="all, delete-orphan", lazy="selectin"
    )


class DictItem(Base):
    __tablename__ = "dict_items"

    id: Mapped[int] = mapped_column(BigIntPK, primary_key=True, autoincrement=True)
    type_id: Mapped[int] = mapped_column(
        ForeignKey("dict_types.id", ondelete="CASCADE"), index=True, nullable=False
    )
    label: Mapped[str] = mapped_column(String(50), nullable=False, comment="显示文案")
    value: Mapped[str] = mapped_column(String(50), nullable=False, comment="存储值")
    sort: Mapped[int] = mapped_column(Integer, default=0, comment="排序，越小越靠前")
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, comment="是否默认")
    status: Mapped[int] = mapped_column(Integer, default=1, comment="1启用 0禁用")
    remark: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    dict_type: Mapped["DictType"] = relationship(back_populates="items")
