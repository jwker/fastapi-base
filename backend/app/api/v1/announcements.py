"""通知公告 API。

管理接口：增删改查 + 发布/下线（announce:read / announce:write，超管与管理角色）。
用户端接口：GET /announcements/public* 仅需登录（所有用户可见已发布公告）。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.response import success
from app.schemas.announcement import (
    AnnouncementCreate,
    AnnouncementOut,
    AnnouncementPage,
    AnnouncementSimple,
    AnnouncementUpdate,
)
from app.services import announcement as announcement_service

router = APIRouter(prefix="/announcements", tags=["通知公告"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


def _out(ann, created_by_name: str = "") -> AnnouncementOut:
    return AnnouncementOut(
        id=ann.id,
        title=ann.title,
        content=ann.content,
        type=ann.type,
        status=ann.status,
        is_top=ann.is_top,
        expire_time=ann.expire_time,
        publish_time=ann.publish_time,
        created_by=ann.created_by,
        created_by_name=created_by_name,
        created_at=ann.created_at,
        updated_at=ann.updated_at,
    )


# ---------- 管理端 ----------


@router.get("")
async def list_announcements(
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("announce:read"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    keyword: str | None = Query(None),
):
    total, rows = await announcement_service.list_announcements(db, page, page_size, keyword)
    return success(AnnouncementPage(total=total, items=[_out(ann, name) for ann, name in rows]))


@router.post("", status_code=201)
async def create_announcement(
    data: AnnouncementCreate,
    db: DbDep,
    user: Annotated[CurrentUser, Depends(require_permission("announce:write"))],
):
    ann = await announcement_service.create_announcement(
        db,
        title=data.title,
        content=data.content,
        type=data.type,
        is_top=data.is_top,
        expire_time=data.expire_time,
        created_by=user.id,
    )
    return success(_out(ann, user.username), "创建成功")


@router.put("/{announcement_id}")
async def update_announcement(
    announcement_id: int,
    data: AnnouncementUpdate,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("announce:write"))],
):
    ann = await announcement_service.update_announcement(
        db,
        announcement_id,
        title=data.title,
        content=data.content,
        type=data.type,
        is_top=data.is_top,
        expire_time=data.expire_time,
    )
    return success(_out(ann), "更新成功")


@router.delete("/{announcement_id}")
async def delete_announcement(
    announcement_id: int,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("announce:write"))],
):
    await announcement_service.delete_announcement(db, announcement_id)
    return success(None, "删除成功")


@router.put("/{announcement_id}/publish")
async def publish_announcement(
    announcement_id: int,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("announce:write"))],
):
    ann = await announcement_service.publish_announcement(db, announcement_id)
    return success(_out(ann), "发布成功")


@router.put("/{announcement_id}/offline")
async def offline_announcement(
    announcement_id: int,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("announce:write"))],
):
    ann = await announcement_service.offline_announcement(db, announcement_id)
    return success(_out(ann), "已下线")


# ---------- 用户端（仅需登录） ----------


@router.get("/public")
async def list_public_announcements(
    db: DbDep,
    _: CurrentUser,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
):
    total, rows = await announcement_service.list_public(db, page, page_size)
    return success(
        {
            "total": total,
            "items": [
                AnnouncementSimple(
                    id=ann.id,
                    title=ann.title,
                    type=ann.type,
                    is_top=ann.is_top,
                    publish_time=ann.publish_time,
                )
                for ann in rows
            ],
        }
    )


@router.get("/public/{announcement_id}")
async def get_public_announcement(
    announcement_id: int,
    db: DbDep,
    _: CurrentUser,
):
    ann = await announcement_service.get_public(db, announcement_id)
    return success(_out(ann))
