"""认证相关 Pydantic 模型。"""

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    id: int
    username: str
    nickname: str
    email: str = ""
    avatar: str = ""
    is_superuser: bool = False
    permissions: list[str] = []
    roles: list[str] = []


class LoginResponse(BaseModel):
    tokens: TokenPair
    user: UserInfo
