"""角色相关 Pydantic 模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RoleBase(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    code: str = Field(min_length=1, max_length=50)
    description: str = Field(default="", max_length=255)
    status: int = Field(default=1, ge=0, le=1)


class RoleCreate(RoleBase):
    pass


class RoleUpdate(BaseModel):
    name: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=255)
    status: int | None = Field(default=None, ge=0, le=1)


class RoleOut(RoleBase):
    id: int
    created_at: datetime
    permission_ids: list[int] = []
    menu_ids: list[int] = []

    model_config = ConfigDict(from_attributes=True)


class RolePage(BaseModel):
    total: int
    items: list[RoleOut]
