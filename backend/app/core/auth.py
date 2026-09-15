"""JWT 双 Token：Access(15min) + Refresh(7d，存 Redis)。"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings
from app.core.redis import KEY_ACCESS_BLACKLIST, KEY_REFRESH_TOKEN, redis_client


def _now() -> datetime:
    return datetime.now(UTC)


def _encode(payload: dict, expires_delta: timedelta) -> str:
    payload = {**payload, "exp": _now() + expires_delta, "jti": uuid.uuid4().hex}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_access_token(user_id: int) -> str:
    return _encode(
        {"sub": str(user_id), "type": "access"},
        timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )


def create_refresh_token(user_id: int) -> str:
    return _encode(
        {"sub": str(user_id), "type": "refresh"}, timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    )


async def decode_token(token: str) -> dict:
    """解码并校验签名/过期，同时检查黑名单。失败抛 jwt 异常。"""
    payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    if payload.get("type") == "access":
        blacklisted = await redis_client.get(f"{KEY_ACCESS_BLACKLIST}:{payload['jti']}")
        if blacklisted:
            raise jwt.InvalidTokenError("token revoked")
    return payload


async def store_refresh_token(user_id: int, refresh_token: str) -> None:
    await redis_client.set(
        f"{KEY_REFRESH_TOKEN}:{user_id}",
        refresh_token,
        ex=timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )


async def verify_refresh_token(user_id: int, refresh_token: str) -> bool:
    stored = await redis_client.get(f"{KEY_REFRESH_TOKEN}:{user_id}")
    return stored == refresh_token


# 原子轮换：校验旧值 + 写入新值一步完成（防并发 refresh 竞态导致 token 分叉）
_REFRESH_ROTATE_SCRIPT = """
local stored = redis.call('GET', KEYS[1])
if stored == ARGV[1] then
  redis.call('SET', KEYS[1], ARGV[2], 'EX', ARGV[3])
  return 1
end
return 0
"""


async def rotate_refresh_token(
    user_id: int, old_token: str, new_token: str, ttl_seconds: int
) -> bool:
    """仅当 Redis 中仍是 old_token 时写入 new_token（CAS）。返回是否轮换成功。"""
    ok = await redis_client.eval(
        _REFRESH_ROTATE_SCRIPT,
        1,
        f"{KEY_REFRESH_TOKEN}:{user_id}",
        old_token,
        new_token,
        ttl_seconds,
    )
    return bool(ok)


async def revoke_refresh_token(user_id: int) -> None:
    await redis_client.delete(f"{KEY_REFRESH_TOKEN}:{user_id}")


async def blacklist_access_token(token: str) -> None:
    """登出时把 Access Token 加入黑名单至其过期。"""
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_exp": True},
        )
        exp = payload.get("exp", 0)
        ttl = max(int(exp - _now().timestamp()), 1)
        await redis_client.setex(f"{KEY_ACCESS_BLACKLIST}:{payload['jti']}", ttl, "1")
    except jwt.PyJWTError:
        pass
