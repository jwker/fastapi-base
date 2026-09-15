"""Redis 客户端（异步）。"""

from redis.asyncio import Redis

from app.core.config import settings

redis_client: Redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)

# 缓存键命名：{app}:{resource}:{id}:{field}
KEY_REFRESH_TOKEN = "app:auth:refresh:{user_id}"
KEY_ACCESS_BLACKLIST = "app:auth:blacklist:{jti}"
KEY_LOGIN_FAIL = "app:auth:login_fail:{username}"
DEFAULT_TTL = 300
