"""权限相关 Pydantic 模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PermissionOut(BaseModel):
    id: int
    name: str
    code: str
    resource: str
    action: str
    description: str = ""
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PermissionPage(BaseModel):
    total: int
    items: list[PermissionOut]
