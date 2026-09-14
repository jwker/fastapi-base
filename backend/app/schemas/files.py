"""文件上传响应模型。"""

from pydantic import BaseModel


class FileOut(BaseModel):
    url: str
    name: str
    size: int
