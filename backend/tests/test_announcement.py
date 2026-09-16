"""通知公告测试：管理端 CRUD/状态流转/权限 + 用户端可见性过滤/置顶排序。"""

import pytest
from httpx import AsyncClient


async def _regular_headers(client: AsyncClient, admin_headers: dict) -> dict:
    """创建普通用户（user 角色）并登录，返回其请求头。"""
    created = await client.post(
        "/api/v1/users", headers=admin_headers, json={"username": "annuser", "password": "ann123"}
    )
    user_id = created.json()["data"]["id"]
    roles = (await client.get("/api/v1/roles", headers=admin_headers)).json()["data"]["items"]
    user_role = next(r for r in roles if r["code"] == "user")
    await client.put(
        f"/api/v1/users/{user_id}", headers=admin_headers, json={"role_ids": [user_role["id"]]}
    )
    login = await client.post(
        "/api/v1/auth/login", json={"username": "annuser", "password": "ann123"}
    )
    token = login.json()["data"]["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def _create_draft(client: AsyncClient, admin_headers: dict, **overrides) -> dict:
    payload = {
        "title": "系统维护通知",
        "content": "本周六凌晨进行系统升级",
        "type": "notice",
        "is_top": False,
        "expire_time": None,
    }
    payload.update(overrides)
    resp = await client.post("/api/v1/announcements", headers=admin_headers, json=payload)
    assert resp.status_code == 201
    return resp.json()["data"]


@pytest.mark.asyncio
async def test_create_defaults_to_draft(client, admin_headers):
    data = await _create_draft(client, admin_headers)
    assert data["status"] == 0
    assert data["type"] == "notice"
    assert data["is_top"] is False
    assert data["created_by_name"] == "admin"


@pytest.mark.asyncio
async def test_create_invalid_type_rejected(client, admin_headers):
    resp = await client.post(
        "/api/v1/announcements",
        headers=admin_headers,
        json={"title": "t", "content": "c", "type": "warning"},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_list_management_includes_all_status(client, admin_headers):
    await _create_draft(client, admin_headers)
    resp = await client.get("/api/v1/announcements", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["title"] == "系统维护通知"
    assert data["items"][0]["content"] == "本周六凌晨进行系统升级"


@pytest.mark.asyncio
async def test_keyword_search_title(client, admin_headers):
    await _create_draft(client, admin_headers, title="安全提醒")
    resp = await client.get("/api/v1/announcements?keyword=安全", headers=admin_headers)
    assert resp.json()["data"]["total"] == 1
    assert resp.json()["data"]["items"][0]["title"] == "安全提醒"


@pytest.mark.asyncio
async def test_publish_sets_status_and_time(client, admin_headers):
    data = await _create_draft(client, admin_headers)
    resp = await client.put(f"/api/v1/announcements/{data['id']}/publish", headers=admin_headers)
    assert resp.status_code == 200
    published = resp.json()["data"]
    assert published["status"] == 1
    assert published["publish_time"] is not None


@pytest.mark.asyncio
async def test_offline_flow(client, admin_headers):
    data = await _create_draft(client, admin_headers)
    await client.put(f"/api/v1/announcements/{data['id']}/publish", headers=admin_headers)
    resp = await client.put(f"/api/v1/announcements/{data['id']}/offline", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["status"] == 2


@pytest.mark.asyncio
async def test_publish_again_rejected(client, admin_headers):
    data = await _create_draft(client, admin_headers)
    await client.put(f"/api/v1/announcements/{data['id']}/publish", headers=admin_headers)
    resp = await client.put(f"/api/v1/announcements/{data['id']}/publish", headers=admin_headers)
    assert resp.status_code == 400
    assert "已发布" in resp.json()["message"]


@pytest.mark.asyncio
async def test_offline_draft_rejected(client, admin_headers):
    data = await _create_draft(client, admin_headers)
    resp = await client.put(f"/api/v1/announcements/{data['id']}/offline", headers=admin_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_update_fields(client, admin_headers):
    data = await _create_draft(client, admin_headers)
    resp = await client.put(
        f"/api/v1/announcements/{data['id']}",
        headers=admin_headers,
        json={"title": "新标题", "is_top": True},
    )
    assert resp.status_code == 200
    updated = resp.json()["data"]
    assert updated["title"] == "新标题"
    assert updated["is_top"] is True
    # status 不受编辑接口影响（仍草稿）
    assert updated["status"] == 0


@pytest.mark.asyncio
async def test_delete_announcement(client, admin_headers):
    data = await _create_draft(client, admin_headers)
    resp = await client.delete(f"/api/v1/announcements/{data['id']}", headers=admin_headers)
    assert resp.status_code == 200
    listed = (await client.get("/api/v1/announcements", headers=admin_headers)).json()["data"]
    assert listed["total"] == 0


@pytest.mark.asyncio
async def test_management_forbidden_for_regular_user(client, admin_headers):
    headers = await _regular_headers(client, admin_headers)
    resp = await client.get("/api/v1/announcements", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_public_list_filters_by_status_and_expire(client, admin_headers):
    """草稿不可见；已发布可见；已下线不可见；过期不可见。"""
    normal = await _create_draft(client, admin_headers)
    await client.put(f"/api/v1/announcements/{normal['id']}/publish", headers=admin_headers)

    await _create_draft(client, admin_headers, title="草稿内容")

    expired = await _create_draft(
        client, admin_headers, title="已过期", expire_time="2020-01-01T00:00:00"
    )
    await client.put(f"/api/v1/announcements/{expired['id']}/publish", headers=admin_headers)

    offline = await _create_draft(client, admin_headers, title="已下线")
    await client.put(f"/api/v1/announcements/{offline['id']}/publish", headers=admin_headers)
    await client.put(f"/api/v1/announcements/{offline['id']}/offline", headers=admin_headers)

    resp = await client.get("/api/v1/announcements/public", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["title"] == "系统维护通知"
    assert "content" not in data["items"][0]  # 列表项不含正文


@pytest.mark.asyncio
async def test_public_top_first(client, admin_headers):
    a = await _create_draft(client, admin_headers, title="普通公告")
    b = await _create_draft(client, admin_headers, title="置顶公告", is_top=True)
    await client.put(f"/api/v1/announcements/{a['id']}/publish", headers=admin_headers)
    await client.put(f"/api/v1/announcements/{b['id']}/publish", headers=admin_headers)

    resp = await client.get("/api/v1/announcements/public", headers=admin_headers)
    items = resp.json()["data"]["items"]
    assert items[0]["title"] == "置顶公告"
    assert items[0]["is_top"] is True


@pytest.mark.asyncio
async def test_public_detail_visible(client, admin_headers):
    data = await _create_draft(client, admin_headers)
    await client.put(f"/api/v1/announcements/{data['id']}/publish", headers=admin_headers)
    resp = await client.get(f"/api/v1/announcements/public/{data['id']}", headers=admin_headers)
    assert resp.status_code == 200
    detail = resp.json()["data"]
    assert detail["content"] == "本周六凌晨进行系统升级"


@pytest.mark.asyncio
async def test_public_detail_hidden_for_draft(client, admin_headers):
    data = await _create_draft(client, admin_headers)
    resp = await client.get(f"/api/v1/announcements/public/{data['id']}", headers=admin_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_public_requires_login(client):
    resp = await client.get("/api/v1/announcements/public")
    assert resp.status_code == 401
