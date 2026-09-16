"""系统参数配置 schema。"""

from datetime import datetime

from pydantic import BaseModel, Field

_VALUE_TYPES = {"string", "int", "bool"}


class ConfigCreate(BaseModel):
    key: str = Field(
        min_length=1, max_length=50, pattern=r"^[a-z][a-z0-9_]*$", description="配置键"
    )
    value: str = Field(min_length=1, max_length=1000, description="配置值")
    value_type: str = Field(default="string", description="值类型标注")
    remark: str = Field(default="", max_length=255)


class ConfigUpdate(BaseModel):
    """更新不提供 key（键不可改，前端编辑时禁用）。"""

    value: str = Field(min_length=1, max_length=1000, description="配置值")
    value_type: str = Field(default="string", description="值类型标注")
    remark: str | None = Field(default=None, max_length=255)


class ConfigOut(BaseModel):
    id: int
    key: str
    value: str
    value_type: str
    remark: str
    created_at: datetime
    updated_at: datetime


class ConfigPage(BaseModel):
    total: int
    items: list[ConfigOut]
