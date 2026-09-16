"""系统参数配置 API。

管理接口：增删改查（config:read / config:write，超管与管理角色）。
业务取用接口：GET /configs/by-key 仅需登录（前端页面按 key 取全局配置）。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.response import success
from app.schemas.config import ConfigCreate, ConfigOut, ConfigPage, ConfigUpdate
from app.services import config as config_service

router = APIRouter(prefix="/configs", tags=["系统参数"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


def _out(c) -> ConfigOut:
    return ConfigOut(
        id=c.id,
        key=c.key,
        value=c.value,
        value_type=c.value_type,
        remark=c.remark,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )


@router.get("")
async def list_configs(
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("config:read"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    keyword: str | None = Query(None),
):
    total, rows = await config_service.list_configs(db, page, page_size, keyword)
    return success(ConfigPage(total=total, items=[_out(c) for c in rows]))


@router.post("", status_code=201)
async def create_config(
    data: ConfigCreate,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("config:write"))],
):
    cfg = await config_service.create_config(
        db, key=data.key, value=data.value, value_type=data.value_type, remark=data.remark
    )
    return success(_out(cfg), "创建成功")


@router.put("/{config_id}")
async def update_config(
    config_id: int,
    data: ConfigUpdate,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("config:write"))],
):
    cfg = await config_service.update_config(
        db, config_id, value=data.value, value_type=data.value_type, remark=data.remark
    )
    return success(_out(cfg), "更新成功")


@router.delete("/{config_id}")
async def delete_config(
    config_id: int,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("config:write"))],
):
    await config_service.delete_config(db, config_id)
    return success(None, "删除成功")


# ---------- 业务取用 ----------


@router.get("/by-key")
async def get_configs_by_keys(
    keys: str,
    db: DbDep,
    _: CurrentUser,
):
    """按逗号分隔的 key 批量读取（仅需登录，业务页取用，不设管理权限）。"""
    key_list = [k.strip() for k in keys.split(",") if k.strip()]
    values = await config_service.get_by_keys(db, key_list)
    return success(values)
