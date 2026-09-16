"""系统参数配置测试：CRUD、key 唯一、权限、读取缓存与失效。"""

import pytest
from httpx import AsyncClient


async def _regular_headers(client: AsyncClient, admin_headers: dict) -> dict:
    """创建普通用户（user 角色）并登录，返回其请求头。"""
    created = await client.post(
        "/api/v1/users", headers=admin_headers, json={"username": "cfguser", "password": "cfg123"}
    )
    user_id = created.json()["data"]["id"]
    roles = (await client.get("/api/v1/roles", headers=admin_headers)).json()["data"]["items"]
    user_role = next(r for r in roles if r["code"] == "user")
    await client.put(
        f"/api/v1/users/{user_id}", headers=admin_headers, json={"role_ids": [user_role["id"]]}
    )
    login = await client.post(
        "/api/v1/auth/login", json={"username": "cfguser", "password": "cfg123"}
    )
    token = login.json()["data"]["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_list_initial_with_seeded_configs(client, admin_headers):
    """种子配置已入库：site_name / upload_max_size 两条。"""
    resp = await client.get("/api/v1/configs", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 2
    keys = {i["key"] for i in data["items"]}
    assert keys == {"site_name", "upload_max_size"}


@pytest.mark.asyncio
async def test_create_config_success(client, admin_headers):
    resp = await client.post(
        "/api/v1/configs",
        headers=admin_headers,
        json={
            "key": "login_fail_limit",
            "value": "5",
            "value_type": "int",
            "remark": "登录失败上限",
        },
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["key"] == "login_fail_limit"
    assert data["value"] == "5"
    assert data["value_type"] == "int"


@pytest.mark.asyncio
async def test_create_duplicate_key_rejected(client, admin_headers):
    resp = await client.post(
        "/api/v1/configs",
        headers=admin_headers,
        json={"key": "site_name", "value": "dup", "value_type": "string"},
    )
    assert resp.status_code == 400
    assert "已存在" in resp.json()["message"]


@pytest.mark.asyncio
async def test_create_invalid_key_rejected(client, admin_headers):
    resp = await client.post(
        "/api/v1/configs",
        headers=admin_headers,
        json={"key": "Site Name", "value": "x", "value_type": "string"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_keyword_search(client, admin_headers):
    resp = await client.get("/api/v1/configs?keyword=site", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["key"] == "site_name"


@pytest.mark.asyncio
async def test_list_forbidden_for_regular_user(client, admin_headers):
    headers = await _regular_headers(client, admin_headers)
    resp = await client.get("/api/v1/configs", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_update_config(client, admin_headers):
    resp = await client.put(
        "/api/v1/configs/1",
        headers=admin_headers,
        json={"value": "MySite", "value_type": "string", "remark": "改后备注"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["value"] == "MySite"
    assert data["remark"] == "改后备注"


@pytest.mark.asyncio
async def test_delete_config(client, admin_headers):
    resp = await client.delete("/api/v1/configs/1", headers=admin_headers)
    assert resp.status_code == 200
    # 删除后列表减少，且读取接口不再返回该 key
    listed = (await client.get("/api/v1/configs", headers=admin_headers)).json()["data"]
    assert listed["total"] == 1
    by_key = (
        await client.get("/api/v1/configs/by-key?keys=site_name", headers=admin_headers)
    ).json()
    assert by_key["data"] == {}


@pytest.mark.asyncio
async def test_by_key_regular_user_can_read(client, admin_headers):
    """业务取用接口仅需登录：普通用户可读种子配置。"""
    headers = await _regular_headers(client, admin_headers)
    resp = await client.get("/api/v1/configs/by-key?keys=site_name,not_exist", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["data"] == {"site_name": "FastAPI Base"}


@pytest.mark.asyncio
async def test_by_key_requires_login(client):
    resp = await client.get("/api/v1/configs/by-key?keys=site_name")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_by_key_cache_invalidated_after_update(client, admin_headers):
    """缓存失效：先读旧值 → 超管更新 → 再读立即拿到新值。"""
    first = (
        await client.get("/api/v1/configs/by-key?keys=site_name", headers=admin_headers)
    ).json()
    assert first["data"]["site_name"] == "FastAPI Base"

    await client.put(
        "/api/v1/configs/1",
        headers=admin_headers,
        json={"value": "NewSite", "value_type": "string"},
    )

    second = (
        await client.get("/api/v1/configs/by-key?keys=site_name", headers=admin_headers)
    ).json()
    assert second["data"]["site_name"] == "NewSite"
