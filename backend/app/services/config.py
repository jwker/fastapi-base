"""系统参数配置服务。

读取走进程内 TTL 缓存（配置低频变动，多实例部署时 TTL 兜底一致性）；
所有写操作后整体失效缓存，保证修改立即可见。
"""

import time

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import AppError
from app.models.config import SysConfig

# 进程内缓存：config_key -> (value, expire_at)；TTL 60s
_CACHE: dict[str, tuple[str, float]] = {}
CACHE_TTL = 60.0


def _clear_cache() -> None:
    _CACHE.clear()


async def list_configs(
    db: AsyncSession, page: int, page_size: int, keyword: str | None = None
) -> tuple[int, list[SysConfig]]:
    stmt = select(SysConfig)
    if keyword:
        stmt = stmt.where(SysConfig.key.contains(keyword) | SysConfig.remark.contains(keyword))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        (
            await db.execute(
                stmt.order_by(SysConfig.id.asc()).offset((page - 1) * page_size).limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    return total, list(rows)


async def get_by_key(db: AsyncSession, key: str) -> str | None:
    """按 key 读取（缓存优先，miss 查库回填；不存在返回 None）。"""
    now = time.monotonic()
    hit = _CACHE.get(key)
    if hit and hit[1] > now:
        return hit[0]
    row = (await db.execute(select(SysConfig).where(SysConfig.key == key))).scalar_one_or_none()
    value = row.value if row else None
    if value is not None:
        _CACHE[key] = (value, now + CACHE_TTL)
    return value


async def get_by_keys(db: AsyncSession, keys: list[str]) -> dict[str, str]:
    """批量读取（缺失的 key 不返回，由调用方处理默认值）。"""
    result: dict[str, str] = {}
    for key in keys:
        value = await get_by_key(db, key)
        if value is not None:
            result[key] = value
    return result


async def create_config(
    db: AsyncSession, key: str, value: str, value_type: str, remark: str = ""
) -> SysConfig:
    exists = (
        await db.execute(select(SysConfig.id).where(SysConfig.key == key))
    ).scalar_one_or_none()
    if exists:
        raise AppError(400, f"配置键 {key} 已存在")
    cfg = SysConfig(key=key, value=value, value_type=value_type, remark=remark)
    db.add(cfg)
    await db.commit()
    await db.refresh(cfg)
    _clear_cache()
    return cfg


async def get_config(db: AsyncSession, config_id: int) -> SysConfig:
    cfg = await db.get(SysConfig, config_id)
    if not cfg:
        raise AppError(404, "配置不存在")
    return cfg


async def update_config(
    db: AsyncSession, config_id: int, value: str, value_type: str, remark: str | None
) -> SysConfig:
    cfg = await get_config(db, config_id)
    cfg.value = value
    cfg.value_type = value_type
    if remark is not None:
        cfg.remark = remark
    await db.commit()
    await db.refresh(cfg)
    _clear_cache()
    return cfg


async def delete_config(db: AsyncSession, config_id: int) -> None:
    cfg = await get_config(db, config_id)
    await db.delete(cfg)
    await db.commit()
    _clear_cache()
