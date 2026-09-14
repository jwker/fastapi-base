"""文件 API：上传（登录即可）、列表（file:read）、删除（file:delete）。

source 由消费端程序自动打标（avatar=头像 / manual=文件管理页手动传），不做用户选择。
"""

import asyncio
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, UploadFile

from app.core.deps import CurrentUser, DbDep, get_current_user, require_permission
from app.core.response import success
from app.schemas.files import FileOut, FilePage
from app.services import file as file_service
from app.services import upload as upload_service

router = APIRouter(prefix="/files", tags=["文件管理"])


@router.post("/upload")
async def upload_file(
    db: DbDep,
    current_user: Annotated[CurrentUser, Depends(get_current_user)],
    file: Annotated[UploadFile, File()],
    source: Annotated[str, Form()] = "manual",
    remark: Annotated[str, Form()] = "",
):
    """上传文件（扩展名白名单 + 大小限制），落盘后写文件记录。

    一致性：先落盘 → 写库失败则删除已落盘文件再报错（防孤儿文件）。
    """
    data = await file.read()
    # 磁盘 IO 放线程池，不阻塞事件循环
    url = await asyncio.to_thread(upload_service.save_upload, data, file.filename or "file")
    try:
        record = await file_service.create_file_record(
            db,
            url=url,
            name=file.filename or "",
            size=len(data),
            mime_type=file.content_type or "",
            source=source or "manual",
            remark=remark or "",
            created_by=current_user.id,
        )
    except Exception:
        # 写库失败：回滚已落盘文件，不留孤儿
        await asyncio.to_thread(upload_service.remove_upload, url)
        raise
    return success(
        FileOut(
            id=record.id,
            url=record.url,
            name=record.name,
            size=record.size,
            mime_type=record.mime_type,
            source=record.source,
            remark=record.remark,
            created_by=record.created_by,
            created_by_name=current_user.username,
            created_at=record.created_at,
        ),
        "上传成功",
    )


@router.get("")
async def list_files(
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("file:read"))],
    page: int = 1,
    page_size: int = 10,
    keyword: str = "",
):
    """文件列表：分页 + 按文件名/备注模糊搜索。"""
    total, rows = await file_service.list_files(db, page, page_size, keyword)
    return success(
        FilePage(
            total=total,
            items=[
                FileOut(
                    id=f.id,
                    url=f.url,
                    name=f.name,
                    size=f.size,
                    mime_type=f.mime_type,
                    source=f.source,
                    remark=f.remark,
                    created_by=f.created_by,
                    created_by_name=uploader,
                    created_at=f.created_at,
                )
                for f, uploader in rows
            ],
        )
    )


@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("file:delete"))],
):
    """删除文件：删记录 + 删磁盘文件（文件已不存在时记录照删，尽力而为）。"""
    record = await file_service.get_file(db, file_id)
    await file_service.delete_file_record(db, record)
    await asyncio.to_thread(upload_service.remove_upload, record.url)
    return success(message="删除成功")
