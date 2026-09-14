"""文件管理接口测试：上传入表、列表/搜索/权限、删除、一致性回滚。"""

import pytest

from app.core.config import settings

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def _monkeypatch_upload_dir(monkeypatch, tmp_path):
    """把上传目录指到临时目录，测试后自动清理。"""
    import app.services.upload as upload_service

    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(upload_service.settings, "UPLOAD_DIR", str(tmp_path))
    return upload_service


async def _upload(client, headers, filename="test.png", content=PNG_BYTES, **kwargs):
    files = {"file": (filename, content, "application/octet-stream")}
    return await client.post("/api/v1/files/upload", files=files, headers=headers, **kwargs)


@pytest.mark.asyncio
async def test_upload_creates_record(client, admin_headers, tmp_path, monkeypatch):
    """上传成功后写入 File 记录：返回 id，记录字段正确。"""
    _monkeypatch_upload_dir(monkeypatch, tmp_path)
    resp = await _upload(client, admin_headers)
    assert resp.status_code in (200, 201)
    data = resp.json()["data"]
    assert data["id"] > 0
    assert data["url"].startswith(f"/{tmp_path.name}/")
    assert data["source"] == "manual"  # 默认来源
    assert data["remark"] == ""
    assert data["created_by_name"]  # 上传人用户名

    # 记录落库（经列表接口验证）
    listed = await client.get("/api/v1/files", headers=admin_headers)
    items = listed.json()["data"]["items"]
    mine = next(i for i in items if i["id"] == data["id"])
    assert mine["name"] == "test.png"
    assert mine["size"] == len(PNG_BYTES)
    assert mine["url"] == data["url"]


@pytest.mark.asyncio
async def test_upload_source_and_remark(client, admin_headers, tmp_path, monkeypatch):
    """显式传 source/remark 落库正确；头像消费端 source=avatar。"""
    _monkeypatch_upload_dir(monkeypatch, tmp_path)
    resp = await _upload(
        client, admin_headers, filename="a.png", data={"source": "avatar", "remark": "我的头像"}
    )
    assert resp.status_code in (200, 201)
    data = resp.json()["data"]
    assert data["source"] == "avatar"
    assert data["remark"] == "我的头像"


@pytest.mark.asyncio
async def test_list_files_pagination_and_search(client, admin_headers, tmp_path, monkeypatch):
    """列表：分页 + 按文件名/备注模糊搜索。"""
    _monkeypatch_upload_dir(monkeypatch, tmp_path)
    for i in range(3):
        await _upload(client, admin_headers, filename=f"report_{i}.png")

    all_resp = await client.get("/api/v1/files", headers=admin_headers)
    assert all_resp.json()["data"]["total"] >= 3

    # 分页：page_size=2 → 只回 2 条
    paged = await client.get("/api/v1/files?page=1&page_size=2", headers=admin_headers)
    assert len(paged.json()["data"]["items"]) == 2

    # 搜索文件名命中
    hit = await client.get("/api/v1/files?keyword=report_2", headers=admin_headers)
    assert hit.json()["data"]["total"] == 1
    assert hit.json()["data"]["items"][0]["name"] == "report_2.png"

    # 搜索备注命中
    await _upload(client, admin_headers, filename="pic.png", data={"remark": "首页轮播"})
    by_remark = await client.get("/api/v1/files?keyword=轮播", headers=admin_headers)
    assert by_remark.json()["data"]["total"] >= 1


@pytest.mark.asyncio
async def test_list_requires_file_read(client, admin_headers, tmp_path, monkeypatch):
    """列表：未登录 401；无 file:read 权限 403。"""
    _monkeypatch_upload_dir(monkeypatch, tmp_path)
    # 未登录
    resp = await client.get("/api/v1/files")
    assert resp.status_code == 401

    # 创建无权限普通用户
    await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": "no_perm", "password": "no_perm123"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "no_perm", "password": "no_perm123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['data']['tokens']['access_token']}"}
    assert (await client.get("/api/v1/files", headers=headers)).status_code == 403


@pytest.mark.asyncio
async def test_delete_file(client, admin_headers, tmp_path, monkeypatch):
    """删除：记录与磁盘文件都消失；再次列表不可见。"""
    _monkeypatch_upload_dir(monkeypatch, tmp_path)
    resp = await _upload(client, admin_headers, filename="del.png")
    file_id = resp.json()["data"]["id"]
    url = resp.json()["data"]["url"]
    rel = url.removeprefix(f"/{tmp_path.name}/")
    assert (tmp_path / rel).exists()

    del_resp = await client.delete(f"/api/v1/files/{file_id}", headers=admin_headers)
    assert del_resp.status_code in (200, 201)
    assert not (tmp_path / rel).exists()  # 磁盘文件被删

    listed = await client.get("/api/v1/files", headers=admin_headers)
    assert all(i["id"] != file_id for i in listed.json()["data"]["items"])


@pytest.mark.asyncio
async def test_delete_file_missing_disk(client, admin_headers, tmp_path, monkeypatch):
    """磁盘文件已被手动清理：记录照删，返回成功（尽力而为）。"""
    _monkeypatch_upload_dir(monkeypatch, tmp_path)
    resp = await _upload(client, admin_headers, filename="gone.png")
    file_id = resp.json()["data"]["id"]
    # 模拟磁盘文件已被清理
    rel = resp.json()["data"]["url"].removeprefix(f"/{tmp_path.name}/")
    (tmp_path / rel).unlink()

    del_resp = await client.delete(f"/api/v1/files/{file_id}", headers=admin_headers)
    assert del_resp.status_code in (200, 201)
    listed = await client.get("/api/v1/files", headers=admin_headers)
    assert all(i["id"] != file_id for i in listed.json()["data"]["items"])


@pytest.mark.asyncio
async def test_delete_requires_file_delete(client, admin_headers, tmp_path, monkeypatch):
    """删除：未登录 401；无 file:delete 权限 403。"""
    _monkeypatch_upload_dir(monkeypatch, tmp_path)
    resp = await _upload(client, admin_headers, filename="guard.png")
    file_id = resp.json()["data"]["id"]

    assert (await client.delete(f"/api/v1/files/{file_id}")).status_code == 401

    await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": "no_del", "password": "no_del123"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"username": "no_del", "password": "no_del123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['data']['tokens']['access_token']}"}
    assert (await client.delete(f"/api/v1/files/{file_id}", headers=headers)).status_code == 403


@pytest.mark.asyncio
async def test_upload_db_failure_rolls_back_disk(client, admin_headers, tmp_path, monkeypatch):
    """写库失败：已落盘文件被清理（防孤儿文件）。"""
    _monkeypatch_upload_dir(monkeypatch, tmp_path)
    import app.api.v1.files as files_api
    import app.services.file as file_service

    real_create = file_service.create_file_record

    async def boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(files_api.file_service, "create_file_record", boom)
    resp = await _upload(client, admin_headers, filename="rollback.png")
    assert resp.status_code == 500
    monkeypatch.setattr(files_api.file_service, "create_file_record", real_create)

    # 磁盘上不应残留文件
    leftovers = list(tmp_path.rglob("*"))
    assert leftovers == [] or all(p.is_dir() for p in leftovers)
