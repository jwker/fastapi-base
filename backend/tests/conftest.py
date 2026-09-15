"""pytest 全局 fixtures：测试库（SQLite 内存）+ 测试客户端 + 种子数据。"""

import os
import sys
import time
from pathlib import Path

# 测试环境：内存 SQLite + 测试 Redis（若不可用则跳过依赖 Redis 的用例）
os.environ.setdefault("APP_ENV", "test")
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret-key-0123456789-0123456789"

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.database import Base, engine
from app.core.security import hash_password
from app.main import app
from app.models.user import User


class FakeRedis:
    """内存版 Redis，用于测试（auth 模块实例方法级替换）。"""

    def __init__(self):
        self._store: dict[str, tuple[str, float]] = {}

    async def get(self, key):
        item = self._store.get(key)
        if item and item[1] < time.time():
            del self._store[key]
            return None
        return item[0] if item else None

    async def set(self, key, value, ex=None):
        if ex is not None:
            seconds = ex.total_seconds() if hasattr(ex, "total_seconds") else ex
            self._store[key] = (value, time.time() + seconds)
        else:
            self._store[key] = (value, float("inf"))
        return True

    async def setex(self, key, ttl, value):
        self._store[key] = (value, time.time() + ttl)
        return True

    async def delete(self, key):
        self._store.pop(key, None)
        return 1

    async def incr(self, key):
        item = self._store.get(key)
        if item and item[1] < time.time():
            del self._store[key]
            item = None
        new_val = (int(item[0]) + 1) if item else 1
        # 保留原 TTL（真实 Redis INCR 语义）
        expire_at = item[1] if item else float("inf")
        self._store[key] = (str(new_val), expire_at)
        return new_val

    async def expire(self, key, seconds):
        item = self._store.get(key)
        if item:
            self._store[key] = (item[0], time.time() + seconds)
            return 1
        return 0

    async def ttl(self, key):
        item = self._store.get(key)
        if not item or item[1] < time.time():
            return -2  # 不存在
        if item[1] == float("inf"):
            return -1  # 无过期
        return int(item[1] - time.time())

    async def eval(self, script, numkeys, *args):
        """模拟 refresh 轮换 Lua 脚本：GET 比对一致才 SET（CAS 原子语义）。"""
        key = args[0]
        old_token, new_token, ttl = args[1], args[2], args[3]
        stored = await self.get(key)
        if stored == old_token:
            await self.set(key, new_token, ex=int(ttl))
            return 1
        return 0


@pytest.fixture(autouse=True)
def fake_redis(monkeypatch):
    """用内存 FakeRedis 替换真实 Redis，避免测试依赖外部服务。"""
    from app.core import redis as redis_module

    fake = FakeRedis()
    for name in ("get", "set", "setex", "delete", "eval", "incr", "expire", "ttl"):
        monkeypatch.setattr(redis_module.redis_client, name, getattr(fake, name))
    yield fake


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    # 每次测试前重建表并种入权限/角色/菜单种子数据
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    from app.core.database import AsyncSessionLocal
    from scripts.init_db import init_dicts, init_menus, init_permissions, init_roles

    async with AsyncSessionLocal() as db:
        with db.no_autoflush:
            perm_mapping = await init_permissions(db)
            roles = await init_roles(db, perm_mapping)
            await init_menus(db, roles)
            await init_dicts(db)
        await db.commit()

    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    # raise_app_exceptions=False：服务端异常转成 500 响应（与真实用户一致），
    # 否则未捕获异常会直接抛给测试（httpx 默认行为）。
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def db():
    from app.core.database import AsyncSessionLocal

    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def admin_user(db):
    user = User(
        username="admin",
        password_hash=hash_password("admin123"),
        nickname="管理员",
        is_superuser=True,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_headers(client, admin_user):
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    )
    token = resp.json()["data"]["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}
