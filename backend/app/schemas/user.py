"""用户相关 Pydantic 模型。"""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserBase(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    nickname: str = Field(default="", max_length=50)
    email: EmailStr | str = ""
    phone: str = Field(default="", max_length=20)
    status: int = Field(default=1, ge=0, le=1)


class UserCreate(UserBase):
    password: str = Field(min_length=6, max_length=128)
    role_ids: list[int] = Field(default_factory=list)


class UserUpdate(BaseModel):
    nickname: str | None = Field(default=None, max_length=50)
    email: EmailStr | str | None = None
    phone: str | None = Field(default=None, max_length=20)
    status: int | None = Field(default=None, ge=0, le=1)
    password: str | None = Field(default=None, min_length=6, max_length=128)
    role_ids: list[int] | None = None


class UserOut(UserBase):
    id: int
    is_superuser: bool = False
    last_login_at: datetime | None = None
    created_at: datetime
    role_ids: list[int] = []

    model_config = ConfigDict(from_attributes=True)


class Page(BaseModel):
    total: int
    items: list


class UserPage(BaseModel):
    total: int
    items: list[UserOut]
