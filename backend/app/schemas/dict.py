"""数据字典 schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class DictTypeBase(BaseModel):
    name: str = Field(min_length=1, max_length=50, description="字典名称")
    type: str = Field(
        min_length=1, max_length=50, pattern=r"^[a-z][a-z0-9_]*$", description="类型编码"
    )
    remark: str = Field(default="", max_length=255)


class DictTypeCreate(DictTypeBase):
    pass


class DictTypeUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    type: str | None = Field(
        default=None, min_length=1, max_length=50, pattern=r"^[a-z][a-z0-9_]*$"
    )
    remark: str | None = Field(default=None, max_length=255)


class DictTypeOut(BaseModel):
    id: int
    name: str
    type: str
    remark: str
    created_at: datetime
    item_count: int = 0


class DictTypePage(BaseModel):
    total: int
    items: list[DictTypeOut]


class DictItemBase(BaseModel):
    label: str = Field(min_length=1, max_length=50, description="显示文案")
    value: str = Field(min_length=1, max_length=50, description="存储值")
    sort: int = Field(default=0)
    is_default: bool = Field(default=False)
    status: int = Field(default=1, ge=0, le=1)
    remark: str = Field(default="", max_length=255)


class DictItemCreate(DictItemBase):
    pass


class DictItemUpdate(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=50)
    value: str | None = Field(default=None, min_length=1, max_length=50)
    sort: int | None = Field(default=None)
    is_default: bool | None = Field(default=None)
    status: int | None = Field(default=None, ge=0, le=1)
    remark: str | None = Field(default=None, max_length=255)


class DictItemOut(DictItemBase):
    id: int
    type_id: int
    created_at: datetime


class DictItemSimple(BaseModel):
    """业务取用字典项（GET /dicts/type/{type} 返回，只含启用项）。"""

    label: str
    value: str
    sort: int
    is_default: bool
