"""文件上传/管理响应模型。"""

from datetime import datetime

from pydantic import BaseModel


class FileOut(BaseModel):
    id: int
    url: str
    name: str
    size: int
    mime_type: str
    source: str
    remark: str
    created_by: int | None
    created_by_name: str = ""
    created_at: datetime


class FilePage(BaseModel):
    total: int
    items: list[FileOut]
