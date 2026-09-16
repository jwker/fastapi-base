"""通知公告 Schema。"""

from datetime import datetime

from pydantic import BaseModel, Field


class AnnouncementCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100, description="标题")
    content: str = Field(min_length=1, description="正文")
    type: str = Field(
        default="notice",
        pattern="^(notice|announcement)$",
        description="notice=通知 / announcement=公告",
    )
    is_top: bool = False
    expire_time: datetime | None = None


class AnnouncementUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    content: str | None = Field(default=None, min_length=1)
    type: str | None = Field(default=None, pattern="^(notice|announcement)$")
    is_top: bool | None = None
    expire_time: datetime | None = None


class AnnouncementOut(BaseModel):
    id: int
    title: str
    content: str
    type: str
    status: int
    is_top: bool
    expire_time: datetime | None
    publish_time: datetime | None
    created_by: int | None
    created_by_name: str = ""
    created_at: datetime
    updated_at: datetime


class AnnouncementPage(BaseModel):
    total: int
    items: list[AnnouncementOut]


class AnnouncementSimple(BaseModel):
    """用户端列表项：不带正文（详情单独取）。"""

    id: int
    title: str
    type: str
    is_top: bool
    publish_time: datetime | None
