"""认证相关 Pydantic 模型。"""

from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(min_length=6, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class ProfileUpdate(BaseModel):
    """个人资料更新：仅允许用户自助修改的字段。"""

    nickname: str | None = Field(default=None, max_length=50)
    email: EmailStr | str | None = None
    phone: str | None = Field(default=None, max_length=20)
    avatar: str | None = Field(default=None, max_length=255)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    id: int
    username: str
    nickname: str
    email: str = ""
    phone: str = ""
    avatar: str = ""
    is_superuser: bool = False
    permissions: list[str] = []
    roles: list[str] = []


class LoginResponse(BaseModel):
    tokens: TokenPair
    user: UserInfo
