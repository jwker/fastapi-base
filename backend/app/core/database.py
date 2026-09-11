"""数据库引擎与会话管理（异步）。"""

from collections.abc import AsyncGenerator

from sqlalchemy import BigInteger
from sqlalchemy.dialects.sqlite import INTEGER as SQLiteInteger
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

# 主键类型：PostgreSQL 用 BIGINT，SQLite 用 INTEGER（否则不自增）
BigIntPK = BigInteger().with_variant(SQLiteInteger(), "sqlite")

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG and not settings.is_prod,
    pool_pre_ping=True,
    connect_args=connect_args,
)

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
