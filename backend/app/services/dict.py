"""数据字典服务。"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.response import AppError
from app.models.dict import DictItem, DictType


async def list_types(
    db: AsyncSession, page: int, page_size: int, keyword: str | None = None
) -> tuple[int, list[DictType], dict[int, int]]:
    """类型分页 + 各项数量映射（count 走独立子查询，避免异步下访问 lazy collection）。"""
    stmt = select(DictType)
    if keyword:
        stmt = stmt.where(DictType.name.contains(keyword) | DictType.type.contains(keyword))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (
        (
            await db.execute(
                stmt.order_by(DictType.id.asc()).offset((page - 1) * page_size).limit(page_size)
            )
        )
        .scalars()
        .all()
    )
    type_ids = [t.id for t in rows]
    counts: dict[int, int] = {}
    if type_ids:
        count_rows = (
            await db.execute(
                select(DictItem.type_id, func.count())
                .where(DictItem.type_id.in_(type_ids))
                .group_by(DictItem.type_id)
            )
        ).all()
        counts = {tid: cnt for tid, cnt in count_rows}
    return total, list(rows), counts


async def get_type(db: AsyncSession, type_id: int) -> DictType:
    t = await db.get(DictType, type_id)
    if not t:
        raise AppError(404, "字典类型不存在")
    return t


async def create_type(db: AsyncSession, name: str, type_code: str, remark: str = "") -> DictType:
    exists = (
        await db.execute(select(DictType.id).where(DictType.type == type_code))
    ).scalar_one_or_none()
    if exists:
        raise AppError(400, "字典类型编码已存在")
    t = DictType(name=name, type=type_code, remark=remark)
    db.add(t)
    await db.commit()
    await db.refresh(t)
    return t


async def update_type(
    db: AsyncSession, type_id: int, name: str | None, type_code: str | None, remark: str | None
) -> DictType:
    t = await get_type(db, type_id)
    if type_code is not None and type_code != t.type:
        exists = (
            await db.execute(select(DictType.id).where(DictType.type == type_code))
        ).scalar_one_or_none()
        if exists:
            raise AppError(400, "字典类型编码已存在")
        t.type = type_code
    if name is not None:
        t.name = name
    if remark is not None:
        t.remark = remark
    await db.commit()
    await db.refresh(t)
    return t


async def delete_type(db: AsyncSession, type_id: int) -> None:
    t = await get_type(db, type_id)
    # items 集合 cascade="all, delete-orphan"，删除类型时级联删除项
    await db.delete(t)
    await db.commit()


async def list_items(db: AsyncSession, type_id: int) -> list[DictItem]:
    await get_type(db, type_id)
    rows = (
        (
            await db.execute(
                select(DictItem).where(DictItem.type_id == type_id).order_by(DictItem.sort.asc())
            )
        )
        .scalars()
        .all()
    )
    return list(rows)


async def create_item(
    db: AsyncSession,
    type_id: int,
    *,
    label: str,
    value: str,
    sort: int,
    is_default: bool,
    status: int,
    remark: str,
) -> DictItem:
    await get_type(db, type_id)
    item = DictItem(
        type_id=type_id,
        label=label,
        value=value,
        sort=sort,
        is_default=is_default,
        status=status,
        remark=remark,
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


async def update_item(
    db: AsyncSession,
    item_id: int,
    *,
    label: str | None,
    value: str | None,
    sort: int | None,
    is_default: bool | None,
    status: int | None,
    remark: str | None,
) -> DictItem:
    item = await db.get(DictItem, item_id)
    if not item:
        raise AppError(404, "字典项不存在")
    if label is not None:
        item.label = label
    if value is not None:
        item.value = value
    if sort is not None:
        item.sort = sort
    if is_default is not None:
        item.is_default = is_default
    if status is not None:
        item.status = status
    if remark is not None:
        item.remark = remark
    await db.commit()
    await db.refresh(item)
    return item


async def delete_item(db: AsyncSession, item_id: int) -> None:
    item = await db.get(DictItem, item_id)
    if not item:
        raise AppError(404, "字典项不存在")
    await db.delete(item)
    await db.commit()


async def get_items_by_type(db: AsyncSession, type_code: str) -> list[DictItem]:
    """按类型编码取启用项（业务取用，未找到类型时返回空列表而非报错）。"""
    t = (await db.execute(select(DictType).where(DictType.type == type_code))).scalar_one_or_none()
    if not t:
        return []
    rows = (
        (
            await db.execute(
                select(DictItem)
                .where(DictItem.type_id == t.id, DictItem.status == 1)
                .order_by(DictItem.sort.asc())
            )
        )
        .scalars()
        .all()
    )
    return list(rows)
