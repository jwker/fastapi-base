"""文件元数据服务：入库、列表（分页/搜索）、删除。"""

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import AppError
from app.models.file import File
from app.models.user import User


async def create_file_record(
    db: AsyncSession,
    *,
    url: str,
    name: str,
    size: int,
    mime_type: str,
    source: str,
    remark: str,
    created_by: int | None,
) -> File:
    """上传落盘后写入文件记录。"""
    record = File(
        url=url,
        name=name,
        size=size,
        mime_type=mime_type,
        source=source,
        remark=remark,
        created_by=created_by,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def list_files(
    db: AsyncSession,
    page: int = 1,
    page_size: int = 10,
    keyword: str = "",
) -> tuple[int, list[tuple[File, str]]]:
    """分页 + 按文件名/备注模糊搜索，返回 (total, [(file, uploader_name)])."""
    stmt = select(File, User.username).join(User, File.created_by == User.id, isouter=True)
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(File.name.like(like), File.remark.like(like)))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    stmt = stmt.order_by(File.created_at.desc(), File.id.desc())
    rows = (await db.execute(stmt.offset((page - 1) * page_size).limit(page_size))).all()
    return total, [(r[0], r[1] or "") for r in rows]


async def get_file(db: AsyncSession, file_id: int) -> File:
    file = (await db.execute(select(File).where(File.id == file_id))).scalar_one_or_none()
    if not file:
        raise AppError(404, "文件不存在")
    return file


async def delete_file_record(db: AsyncSession, file: File) -> None:
    """删除文件记录（磁盘文件由调用方负责清理）。"""
    await db.delete(file)
    await db.commit()
