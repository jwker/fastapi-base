"""操作审计日志测试：写操作落库/脱敏/动作推断/权限/筛选。"""

import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.operation_log import OperationLog


async def _logs() -> list[OperationLog]:
    async with AsyncSessionLocal() as db:
        return (
            (await db.execute(select(OperationLog).order_by(OperationLog.id.desc())))
            .scalars()
            .all()
        )


@pytest.mark.asyncio
async def test_create_user_logged_with_masked_body(client, admin_headers):
    """创建用户 → 落库 create 日志，body 密码全量脱敏、手机号部分脱敏。"""
    before = len(await _logs())
    resp = await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": "audit_alice", "password": "secret123", "phone": "13800138000"},
    )
    assert resp.status_code in (200, 201)

    logs = await _logs()
    assert len(logs) == before + 1
    log = logs[0]
    assert log.action == "create"
    assert log.module == "用户管理"
    assert log.method == "POST"
    assert log.path == "/api/v1/users"
    assert log.username == "admin"
    assert log.response_status == 201
    assert "secret123" not in log.request_body
    assert "******" in log.request_body
    assert "138****8000" in log.request_body


@pytest.mark.asyncio
async def test_update_and_delete_actions(client, admin_headers):
    """PUT → update、DELETE → delete 动作推断正确。"""
    created = await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": "audit_bob", "password": "bob12345"},
    )
    user_id = created.json()["data"]["id"]

    await client.put(f"/api/v1/users/{user_id}", headers=admin_headers, json={"nickname": "改名"})
    logs = await _logs()
    assert logs[0].action == "update"
    assert logs[0].method == "PUT"

    await client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)
    logs = await _logs()
    assert logs[0].action == "delete"
    assert logs[0].method == "DELETE"


@pytest.mark.asyncio
async def test_get_not_logged(client, admin_headers):
    """GET 请求不落审计日志。"""
    await client.get("/api/v1/users", headers=admin_headers)
    logs = await _logs()
    assert logs and all(log.method != "GET" for log in logs)


@pytest.mark.asyncio
async def test_failed_login_logged_anonymous(client):
    """登录失败也落库：action=login，user_id 空但记录登录名。"""
    before = len(await _logs())
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "nobody", "password": "wrong123"}
    )
    assert resp.status_code in (400, 401)

    logs = await _logs()
    assert len(logs) == before + 1
    log = logs[0]
    assert log.action == "login"
    assert log.module == "认证"
    assert log.user_id is None
    assert log.username == "nobody"  # 登录日志记登录名（业界做法）
    assert "wrong123" not in log.request_body


@pytest.mark.asyncio
async def test_login_success_logged_with_username(client):
    """登录成功落库：记录登录名，user_id 留空（登录时无登录态）。"""
    await client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123"})
    logs = await _logs()
    assert logs[0].action == "login"
    assert logs[0].username == "admin"
    assert logs[0].user_id is None


@pytest.mark.asyncio
async def test_logout_logged_with_operator(client, admin_headers):
    """登出落库：能解析到操作人（请求进入时 token 尚未被黑名单）。"""
    await client.post("/api/v1/auth/logout", headers=admin_headers, json={"refresh_token": "x"})
    logs = await _logs()
    assert logs[0].action == "logout"
    assert logs[0].username == "admin"
    assert logs[0].user_id is not None


@pytest.mark.asyncio
async def test_audit_list_and_filter(client, admin_headers):
    """超管可查列表，按 username/module 筛选生效。"""
    await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": "audit_filter", "password": "pass12345"},
    )
    resp = await client.get(
        "/api/v1/audit-logs?page=1&page_size=10&username=admin&module=用户管理",
        headers=admin_headers,
    )
    assert resp.status_code in (200, 201)
    data = resp.json()["data"]
    assert data["total"] >= 1
    assert data["items"][0]["action"] == "create"
    assert "******" in data["items"][0]["request_body"]

    # 筛选不存在操作人 → 0 条
    resp = await client.get("/api/v1/audit-logs?username=nobody", headers=admin_headers)
    assert resp.json()["data"]["total"] == 0


@pytest.mark.asyncio
async def test_audit_list_forbidden_for_normal_user(client, admin_headers):
    """普通用户无 audit:read → 403。"""
    created = await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": "audit_lily", "password": "lily12345"},
    )
    user_id = created.json()["data"]["id"]
    roles = (await client.get("/api/v1/roles", headers=admin_headers)).json()["data"]["items"]
    user_role = next(r for r in roles if r["code"] == "user")
    await client.put(
        f"/api/v1/users/{user_id}", headers=admin_headers, json={"role_ids": [user_role["id"]]}
    )
    login = await client.post(
        "/api/v1/auth/login", json={"username": "audit_lily", "password": "lily12345"}
    )
    lily_headers = {"Authorization": f"Bearer {login.json()['data']['tokens']['access_token']}"}

    resp = await client.get("/api/v1/audit-logs", headers=lily_headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_excluded_paths_not_logged(client):
    """排除路径（/docs 等）即使写方法也不记录。"""
    before = len(await _logs())
    await client.post("/docs", json={})
    logs = await _logs()
    assert len(logs) == before
    assert all(log.path != "/docs" for log in logs)
