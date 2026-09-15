"""登录失败锁定：Redis 计数（滑动窗口），对齐 RuoYi 5 次 / 10 分钟。

- key：`app:auth:login_fail:{username}`，值为失败次数，TTL = 锁定分钟数
- 每次失败刷新 TTL（滑动窗口）：10 分钟内累计 N 次即锁定，防"分散尝试绕过"
- `incr` 原子操作：并发爆破不丢计数
- 锁定由 TTL 到期自动解锁（无需手动解锁）
"""

import math

from app.core.config import settings
from app.core.redis import KEY_LOGIN_FAIL, redis_client


def _key(username: str) -> str:
    return KEY_LOGIN_FAIL.format(username=username)


async def get_login_fail(username: str) -> tuple[int, int]:
    """返回 (失败次数, 剩余锁定秒数)；无记录时返回 (0, 0)。"""
    key = _key(username)
    count = await redis_client.get(key)
    if count is None:
        return 0, 0
    ttl = await redis_client.ttl(key)
    return int(count), max(ttl, 0)


async def record_login_fail(username: str) -> int:
    """失败计数 +1（原子 incr，滑动窗口刷新 TTL）。返回最新计数。"""
    key = _key(username)
    count = await redis_client.incr(key)
    await redis_client.expire(key, settings.LOGIN_LOCK_MINUTES * 60)
    return count


async def clear_login_fail(username: str) -> None:
    """登录成功时清零失败计数。"""
    await redis_client.delete(_key(username))


async def lock_remaining_minutes(username: str) -> int:
    """锁定剩余分钟数（向上取整，至少 1）。未锁定时返回 0。"""
    count, ttl = await get_login_fail(username)
    if count < settings.LOGIN_FAIL_LIMIT:
        return 0
    return max(math.ceil(ttl / 60), 1)
