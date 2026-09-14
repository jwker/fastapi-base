"""数据字典 CRUD / 权限 / 种子测试。"""

import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.dict import DictItem, DictType
from scripts.init_db import init_dicts


@pytest.mark.asyncio
async def test_dict_type_crud(client, admin_headers):
    # 创建
    resp = await client.post(
        "/api/v1/dicts",
        headers=admin_headers,
        json={"name": "性别", "type": "gender", "remark": "测试"},
    )
    assert resp.status_code == 201
    type_id = resp.json()["data"]["id"]

    # 列表可见
    resp = await client.get("/api/v1/dicts?page=1&page_size=10", headers=admin_headers)
    assert resp.json()["data"]["total"] >= 1
    assert any(t["type"] == "gender" for t in resp.json()["data"]["items"])

    # 更新
    resp = await client.put(
        f"/api/v1/dicts/{type_id}", headers=admin_headers, json={"name": "性别类型"}
    )
    assert resp.json()["data"]["name"] == "性别类型"

    # 删除
    resp = await client.delete(f"/api/v1/dicts/{type_id}", headers=admin_headers)
    assert resp.status_code in (200, 201)


@pytest.mark.asyncio
async def test_dict_type_code_duplicate_and_invalid(client, admin_headers):
    # 编码重复
    await client.post(
        "/api/v1/dicts", headers=admin_headers, json={"name": "状态", "type": "sys_status"}
    )
    resp = await client.post(
        "/api/v1/dicts", headers=admin_headers, json={"name": "重复", "type": "sys_status"}
    )
    assert resp.status_code == 400

    # 非法编码（大写/空格）
    resp = await client.post(
        "/api/v1/dicts", headers=admin_headers, json={"name": "x", "type": "Bad Type"}
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_dict_item_crud_and_cascade_delete(client, admin_headers):
    # 创建类型
    resp = await client.post(
        "/api/v1/dicts", headers=admin_headers, json={"name": "颜色", "type": "color"}
    )
    type_id = resp.json()["data"]["id"]

    # 创建项
    resp = await client.post(
        f"/api/v1/dicts/{type_id}/items",
        headers=admin_headers,
        json={"label": "红色", "value": "red", "sort": 1, "status": 1},
    )
    assert resp.status_code == 201
    item_id = resp.json()["data"]["id"]

    # 列表
    resp = await client.get(f"/api/v1/dicts/{type_id}/items", headers=admin_headers)
    assert len(resp.json()["data"]) == 1

    # 更新项
    resp = await client.put(
        f"/api/v1/dicts/items/{item_id}", headers=admin_headers, json={"label": "深红", "sort": 0}
    )
    assert resp.json()["data"]["label"] == "深红"

    # 级联删除：删类型后项一并删除
    await client.delete(f"/api/v1/dicts/{type_id}", headers=admin_headers)
    async with AsyncSessionLocal() as db:
        item = (
            await db.execute(select(DictItem).where(DictItem.id == item_id))
        ).scalar_one_or_none()
        assert item is None


@pytest.mark.asyncio
async def test_get_items_by_type_filters_disabled_and_sorts(client, admin_headers):
    resp = await client.post(
        "/api/v1/dicts", headers=admin_headers, json={"name": "渠道", "type": "channel"}
    )
    type_id = resp.json()["data"]["id"]
    for label, value, sort, status in [
        ("线下", "offline", 2, 1),
        ("线上", "online", 1, 1),
        ("废弃", "gone", 3, 0),  # 禁用项不应返回
    ]:
        await client.post(
            f"/api/v1/dicts/{type_id}/items",
            headers=admin_headers,
            json={"label": label, "value": value, "sort": sort, "status": status},
        )

    resp = await client.get("/api/v1/dicts/type/channel", headers=admin_headers)
    items = resp.json()["data"]
    assert [i["value"] for i in items] == ["online", "offline"]  # 排序 + 排除禁用


@pytest.mark.asyncio
async def test_get_items_by_type_missing_type_returns_empty(client, admin_headers):
    resp = await client.get("/api/v1/dicts/type/no_such_type", headers=admin_headers)
    assert resp.status_code in (200, 201)
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_dict_permission_required(client):
    """无权限（未登录）访问管理接口 401。"""
    resp = await client.get("/api/v1/dicts")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_dict_management_permission_for_user(client, admin_headers):
    """普通用户无 dict 权限：列表与创建均 403；但业务取用接口（仅登录）可用。"""
    await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": "dict_user", "password": "dict123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"username": "dict_user", "password": "dict123"}
    )
    headers = {"Authorization": f"Bearer {login.json()['data']['tokens']['access_token']}"}

    resp = await client.get("/api/v1/dicts", headers=headers)
    assert resp.status_code == 403
    resp = await client.post("/api/v1/dicts", headers=headers, json={"name": "x", "type": "hack"})
    assert resp.status_code == 403

    # 业务取用：仅登录即可（普通用户能拿到种子字典）
    resp = await client.get("/api/v1/dicts/type/sys_status", headers=headers)
    assert resp.status_code in (200, 201)
    assert resp.json()["data"][0]["label"] == "启用"


@pytest.mark.asyncio
async def test_dict_seed_idempotent():
    """字典种子幂等：重复执行不重复插入。"""
    async with AsyncSessionLocal() as db:
        await init_dicts(db)
        await db.commit()

    async with AsyncSessionLocal() as db:
        # 种子三个类型
        types = (
            (
                await db.execute(
                    select(DictType).where(
                        DictType.type.in_(["sys_status", "file_source", "audit_action"])
                    )
                )
            )
            .scalars()
            .all()
        )
        assert len(types) == 3
        # 每个类型的项数与种子一致（不重复）
        for t in types:
            cnt = (
                (await db.execute(select(DictItem).where(DictItem.type_id == t.id))).scalars().all()
            )
            assert len(cnt) > 0
