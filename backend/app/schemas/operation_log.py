"""操作审计日志相关 Pydantic 模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class OperationLogOut(BaseModel):
    id: int
    user_id: int | None = None
    username: str = ""
    module: str = ""
    action: str = ""
    method: str
    path: str
    request_body: str = ""
    response_status: int
    ip: str = ""
    user_agent: str = ""
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OperationLogPage(BaseModel):
    total: int
    items: list[OperationLogOut]
