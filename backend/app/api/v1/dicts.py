"""数据字典管理 API。

管理接口：类型/项的增删改查（dict:read / dict:write）。
业务取用接口：GET /dicts/type/{type} 仅需登录（下拉/标签显示场景，不设管理权限）。
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import CurrentUser, require_permission
from app.core.response import success
from app.schemas.dict import (
    DictItemCreate,
    DictItemOut,
    DictItemSimple,
    DictItemUpdate,
    DictTypeCreate,
    DictTypeOut,
    DictTypePage,
    DictTypeUpdate,
)
from app.services import dict as dict_service

router = APIRouter(prefix="/dicts", tags=["数据字典"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


def _type_out(t, item_count: int) -> DictTypeOut:
    return DictTypeOut(
        id=t.id,
        name=t.name,
        type=t.type,
        remark=t.remark,
        created_at=t.created_at,
        item_count=item_count,
    )


def _item_out(i) -> DictItemOut:
    return DictItemOut(
        id=i.id,
        type_id=i.type_id,
        label=i.label,
        value=i.value,
        sort=i.sort,
        is_default=i.is_default,
        status=i.status,
        remark=i.remark,
        created_at=i.created_at,
    )


# ---------- 类型管理 ----------


@router.get("")
async def list_dict_types(
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("dict:read"))],
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    keyword: str | None = Query(None),
):
    total, rows, counts = await dict_service.list_types(db, page, page_size, keyword)
    return success(
        DictTypePage(total=total, items=[_type_out(t, counts.get(t.id, 0)) for t in rows])
    )


@router.post("", status_code=201)
async def create_dict_type(
    data: DictTypeCreate,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("dict:write"))],
):
    t = await dict_service.create_type(db, name=data.name, type_code=data.type, remark=data.remark)
    return success(_type_out(t, 0), "创建成功")


@router.put("/{type_id}")
async def update_dict_type(
    type_id: int,
    data: DictTypeUpdate,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("dict:write"))],
):
    t = await dict_service.update_type(
        db, type_id, name=data.name, type_code=data.type, remark=data.remark
    )
    return success(_type_out(t, 0), "更新成功")


@router.delete("/{type_id}")
async def delete_dict_type(
    type_id: int,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("dict:write"))],
):
    await dict_service.delete_type(db, type_id)
    return success(None, "删除成功")


# ---------- 字典项管理 ----------


@router.get("/{type_id}/items")
async def list_dict_items(
    type_id: int,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("dict:read"))],
):
    rows = await dict_service.list_items(db, type_id)
    return success([_item_out(i) for i in rows])


@router.post("/{type_id}/items", status_code=201)
async def create_dict_item(
    type_id: int,
    data: DictItemCreate,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("dict:write"))],
):
    i = await dict_service.create_item(
        db,
        type_id,
        label=data.label,
        value=data.value,
        sort=data.sort,
        is_default=data.is_default,
        status=data.status,
        remark=data.remark,
    )
    return success(_item_out(i), "创建成功")


@router.put("/items/{item_id}")
async def update_dict_item(
    item_id: int,
    data: DictItemUpdate,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("dict:write"))],
):
    i = await dict_service.update_item(
        db,
        item_id,
        label=data.label,
        value=data.value,
        sort=data.sort,
        is_default=data.is_default,
        status=data.status,
        remark=data.remark,
    )
    return success(_item_out(i), "更新成功")


@router.delete("/items/{item_id}")
async def delete_dict_item(
    item_id: int,
    db: DbDep,
    _: Annotated[CurrentUser, Depends(require_permission("dict:write"))],
):
    await dict_service.delete_item(db, item_id)
    return success(None, "删除成功")


# ---------- 业务取用 ----------


@router.get("/type/{type_code}")
async def get_items_by_type(
    type_code: str,
    db: DbDep,
    _: CurrentUser,
):
    """按类型编码取启用项（仅需登录，业务下拉/标签显示用，不设管理权限）。"""
    rows = await dict_service.get_items_by_type(db, type_code)
    return success(
        [
            DictItemSimple(label=i.label, value=i.value, sort=i.sort, is_default=i.is_default)
            for i in rows
        ]
    )
