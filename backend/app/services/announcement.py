"""通知公告服务。

管理端：CRUD + 发布/下线状态流转（发布时写 publish_time）。
用户端：仅已发布且未过期，置顶优先 + 发布时间倒序。
"""

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import AppError
from app.models.announcement import Announcement
from app.models.user import User

STATUS_DRAFT = 0
STATUS_PUBLISHED = 1
STATUS_OFFLINE = 2


def _now() -> datetime:
    return datetime.now()


async def list_announcements(
    db: AsyncSession, page: int, page_size: int, keyword: str | None = None
) -> tuple[int, list[tuple[Announcement, str]]]:
    """管理端分页：全部状态 + 标题/正文模糊搜索，返回 (total, [(ann, uploader_name)])。"""
    stmt = select(Announcement, User.username).join(
        User, Announcement.created_by == User.id, isouter=True
    )
    if keyword:
        like = f"%{keyword}%"
        stmt = stmt.where(or_(Announcement.title.like(like), Announcement.content.like(like)))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        await db.execute(
            stmt.order_by(Announcement.id.desc()).offset((page - 1) * page_size).limit(page_size)
        )
    ).all()
    return total, [(r[0], r[1] or "") for r in rows]


async def get_announcement(db: AsyncSession, announcement_id: int) -> Announcement:
    ann = await db.get(Announcement, announcement_id)
    if not ann:
        raise AppError(404, "公告不存在")
    return ann


async def create_announcement(
    db: AsyncSession,
    title: str,
    content: str,
    type: str,
    is_top: bool,
    expire_time: datetime | None,
    created_by: int,
) -> Announcement:
    ann = Announcement(
        title=title,
        content=content,
        type=type,
        status=STATUS_DRAFT,
        is_top=is_top,
        expire_time=expire_time,
        created_by=created_by,
    )
    db.add(ann)
    await db.commit()
    await db.refresh(ann)
    return ann


async def update_announcement(
    db: AsyncSession,
    announcement_id: int,
    title: str | None,
    content: str | None,
    type: str | None,
    is_top: bool | None,
    expire_time: datetime | None,
) -> Announcement:
    """编辑正文等字段（status 不受此接口影响，由 publish/offline 控制）。"""
    ann = await get_announcement(db, announcement_id)
    if title is not None:
        ann.title = title
    if content is not None:
        ann.content = content
    if type is not None:
        ann.type = type
    if is_top is not None:
        ann.is_top = is_top
    ann.expire_time = expire_time
    await db.commit()
    await db.refresh(ann)
    return ann


async def delete_announcement(db: AsyncSession, announcement_id: int) -> None:
    ann = await get_announcement(db, announcement_id)
    await db.delete(ann)
    await db.commit()


async def publish_announcement(db: AsyncSession, announcement_id: int) -> Announcement:
    ann = await get_announcement(db, announcement_id)
    if ann.status == STATUS_PUBLISHED:
        raise AppError(400, "公告已发布")
    ann.status = STATUS_PUBLISHED
    ann.publish_time = _now()
    await db.commit()
    await db.refresh(ann)
    return ann


async def offline_announcement(db: AsyncSession, announcement_id: int) -> Announcement:
    ann = await get_announcement(db, announcement_id)
    if ann.status != STATUS_PUBLISHED:
        raise AppError(400, "仅已发布公告可下线")
    ann.status = STATUS_OFFLINE
    await db.commit()
    await db.refresh(ann)
    return ann


async def list_public(
    db: AsyncSession, page: int, page_size: int
) -> tuple[int, list[Announcement]]:
    """用户端列表：已发布且未过期；置顶优先 + 发布时间倒序。"""
    now = _now()
    cond = [
        Announcement.status == STATUS_PUBLISHED,
        (Announcement.expire_time.is_(None)) | (Announcement.expire_time > now),
    ]
    stmt = select(Announcement).where(*cond)
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        (
            await db.execute(
                stmt.order_by(Announcement.is_top.desc(), Announcement.publish_time.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return total, list(rows)


async def get_public(db: AsyncSession, announcement_id: int) -> Announcement:
    """用户端详情：仅已发布且未过期，否则 404（不暴露存在性）。"""
    now = _now()
    ann = (
        await db.execute(
            select(Announcement).where(
                Announcement.id == announcement_id,
                Announcement.status == STATUS_PUBLISHED,
                (Announcement.expire_time.is_(None)) | (Announcement.expire_time > now),
            )
        )
    ).scalar_one_or_none()
    if not ann:
        raise AppError(404, "公告不存在")
    return ann
