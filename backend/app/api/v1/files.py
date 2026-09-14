"""文件上传 API：登录即可上传，业务权限在关联处控制。"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.core.deps import CurrentUser, get_current_user
from app.core.response import success
from app.schemas.files import FileOut
from app.services import upload as upload_service

router = APIRouter(prefix="/files", tags=["文件管理"])


@router.post("/upload")
def upload_file(
    _: Annotated[CurrentUser, Depends(get_current_user)],
    file: Annotated[UploadFile, File()],
):
    """上传文件（扩展名白名单 + 大小限制），返回可访问 URL。

    同步端点：磁盘 IO 由 FastAPI 放入线程池执行，不阻塞事件循环。
    """
    data = file.file.read()
    url = upload_service.save_upload(data, file.filename or "file")
    return success(FileOut(url=url, name=file.filename or "", size=len(data)), "上传成功")
