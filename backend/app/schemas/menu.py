"""菜单相关 Pydantic 模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class MenuBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    path: str = Field(min_length=1, max_length=100)
    component: str = Field(default="", max_length=100)
    icon: str = Field(default="", max_length=50)
    sort_order: int = Field(default=0)
    is_visible: bool = Field(default=True)
    permission_code: str | None = Field(default=None, max_length=100)


class MenuCreate(MenuBase):
    parent_id: int | None = None


class MenuUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=50)
    path: str | None = Field(default=None, max_length=100)
    component: str | None = Field(default=None, max_length=100)
    icon: str | None = Field(default=None, max_length=50)
    sort_order: int | None = None
    is_visible: bool | None = None
    permission_code: str | None = None
    parent_id: int | None = None


class MenuOut(MenuBase):
    id: int
    parent_id: int | None
    created_at: datetime
    children: list["MenuOut"] = []

    model_config = ConfigDict(from_attributes=True)


MenuOut.model_rebuild()
