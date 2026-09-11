"""操作审计日志：导出（CSV）与导出后删除测试。"""

import csv
import io

import pytest
from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.models.operation_log import OperationLog
from app.services import audit as audit_service


async def _count() -> int:
    async with AsyncSessionLocal() as db:
        from sqlalchemy import func

        return (await db.execute(select(func.count()).select_from(OperationLog))).scalar_one()


async def _parse_csv(resp) -> list[list[str]]:
    """从响应流解析 CSV（跳过 BOM）。"""
    content = resp.content.decode("utf-8-sig")
    return list(csv.reader(io.StringIO(content)))


@pytest.mark.asyncio
async def test_export_csv_content(client, admin_headers):
    """导出 CSV：表头 + 数据行正确，BOM 使 Excel 中文不乱码。"""
    await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": "exp_alice", "password": "alice12345"},
    )
    resp = await client.get("/api/v1/audit-logs/export", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]

    rows = await _parse_csv(resp)
    # 删除动作自身也会被审计（+1 条），故 before - after = deleted - 1
    assert rows[0] == [
        "ID",
        "操作人",
        "模块",
        "动作",
        "方法",
        "路径",
        "状态码",
        "IP",
        "操作时间",
        "请求参数",
    ]
    assert any(r[1] == "admin" and r[3] == "create" for r in rows)
    # 请求参数脱敏后导出
    assert any("******" in r[9] for r in rows)


@pytest.mark.asyncio
async def test_export_with_filter(client, admin_headers):
    """导出按筛选条件过滤。"""
    await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": "exp_bob", "password": "bob12345"},
    )
    resp = await client.get(
        "/api/v1/audit-logs/export?module=用户管理&username=admin",
        headers=admin_headers,
    )
    rows = await _parse_csv(resp)
    data_rows = rows[1:]
    assert data_rows  # 有数据
    assert all(r[2] == "用户管理" and r[1] == "admin" for r in data_rows)


@pytest.mark.asyncio
async def test_export_empty_only_header(client, admin_headers):
    """导出空数据：仅表头，可正常下载。"""
    resp = await client.get(
        "/api/v1/audit-logs/export?username=no_such_user_xyz", headers=admin_headers
    )
    assert resp.status_code == 200
    rows = await _parse_csv(resp)
    assert len(rows) == 1
    assert rows[0][0] == "ID"


@pytest.mark.asyncio
async def test_export_over_limit_400(client, admin_headers, monkeypatch):
    """导出超上限 → 400 提示缩小范围。"""
    monkeypatch.setattr(audit_service, "MAX_EXPORT_ROWS", 2)
    await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": "exp_over1", "password": "over12345"},
    )
    await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": "exp_over2", "password": "over12345"},
    )
    await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": "exp_over3", "password": "over12345"},
    )
    resp = await client.get("/api/v1/audit-logs/export", headers=admin_headers)
    assert resp.status_code == 400
    assert "缩小筛选范围" in resp.json()["message"]


@pytest.mark.asyncio
async def test_delete_within_export_range(client, admin_headers):
    """删除范围=导出范围：同筛选 + created_at<=end_time。"""
    await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": "del_alice", "password": "alice12345"},
    )
    await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": "del_bob", "password": "bob12345"},
    )
    before = await _count()

    resp = await client.delete(
        "/api/v1/audit-logs?module=用户管理&username=admin&end_time=2099-12-31T23:59:59",
        headers=admin_headers,
    )
    assert resp.status_code in (200, 201)
    deleted = resp.json()["data"]["deleted"]
    assert deleted >= 2

    after = await _count()
    # 删除动作自身被审计（+1），故 after = before - deleted + 1
    assert before - after == deleted - 1
    # 剩余日志不应包含用户管理模块的 create 记录
    async with AsyncSessionLocal() as db:
        rows = (
            (
                await db.execute(
                    select(OperationLog).where(
                        OperationLog.module == "用户管理", OperationLog.action == "create"
                    )
                )
            )
            .scalars()
            .all()
        )
        assert not rows


@pytest.mark.asyncio
async def test_delete_respects_end_time_boundary(client, admin_headers):
    """删除边界：end_time 之后的数据不被删除。"""
    await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": "bound_alice", "password": "alice12345"},
    )
    before = await _count()

    # end_time 设为 2000 年 → 不删任何数据（边界之前无日志）；删除动作自身被审计 +1
    resp = await client.delete(
        "/api/v1/audit-logs?end_time=2000-01-01T00:00:00",
        headers=admin_headers,
    )
    assert resp.status_code in (200, 201)
    assert resp.json()["data"]["deleted"] == 0
    assert await _count() == before + 1


@pytest.mark.asyncio
async def test_delete_requires_end_time(client, admin_headers):
    """删除必须带 end_time（导出时刻边界），缺省 → 422。"""
    resp = await client.delete("/api/v1/audit-logs", headers=admin_headers)
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_delete_forbidden_for_normal_user(client, admin_headers):
    """普通用户无 audit:delete → 403。"""
    created = await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": "del_lily", "password": "lily12345"},
    )
    user_id = created.json()["data"]["id"]
    roles = (await client.get("/api/v1/roles", headers=admin_headers)).json()["data"]["items"]
    user_role = next(r for r in roles if r["code"] == "user")
    await client.put(
        f"/api/v1/users/{user_id}", headers=admin_headers, json={"role_ids": [user_role["id"]]}
    )
    login = await client.post(
        "/api/v1/auth/login", json={"username": "del_lily", "password": "lily12345"}
    )
    lily_headers = {"Authorization": f"Bearer {login.json()['data']['tokens']['access_token']}"}

    resp = await client.delete(
        "/api/v1/audit-logs?end_time=2099-12-31T23:59:59", headers=lily_headers
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_itself_is_audited(client, admin_headers):
    """删除日志的行为本身被审计记录（闭环）。"""
    resp = await client.delete(
        "/api/v1/audit-logs?end_time=2099-12-31T23:59:59", headers=admin_headers
    )
    deleted = resp.json()["data"]["deleted"]
    assert deleted >= 0
    logs = await _logs()
    assert logs[0].action == "delete"
    assert logs[0].module == "操作日志"
    assert logs[0].username == "admin"
    assert logs[0].response_status in (200, 201)


async def _logs():
    async with AsyncSessionLocal() as db:
        return (
            (await db.execute(select(OperationLog).order_by(OperationLog.id.desc())))
            .scalars()
            .all()
        )
