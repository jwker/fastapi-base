"""文件上传接口测试：校验、落盘、权限、文件名安全。"""

import pytest

from app.core.config import settings

PNG_BYTES = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


async def _upload(client, headers, filename="test.png", content=PNG_BYTES, **kwargs):
    files = {"file": (filename, content, "application/octet-stream")}
    return await client.post("/api/v1/files/upload", files=files, headers=headers, **kwargs)


@pytest.mark.asyncio
async def test_upload_success_and_file_exists(client, admin_headers, tmp_path):
    """合法文件上传：200、返回 /uploads/ URL、文件真实落盘到配置目录。"""
    import app.services.upload as upload_service

    # 把上传目录指到临时目录，测试后自动清理
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(upload_service.settings, "UPLOAD_DIR", str(tmp_path))

    resp = await _upload(client, admin_headers)
    monkeypatch.undo()
    assert resp.status_code in (200, 201)
    data = resp.json()["data"]
    # URL 前缀 = UPLOAD_DIR 目录名（monkeypatch 后为 tmp_path 名；真实部署为 uploads）
    assert data["url"].startswith(f"/{tmp_path.name}/")
    assert data["url"].endswith(".png")
    assert data["size"] == len(PNG_BYTES)
    # 文件真实落盘（相对 URL 去掉前缀即相对目录路径）
    rel = data["url"].removeprefix(f"/{tmp_path.name}/")
    assert (tmp_path / rel).exists()
    assert (tmp_path / rel).read_bytes() == PNG_BYTES


@pytest.mark.asyncio
async def test_upload_empty_file(client, admin_headers):
    """空文件 → 400。"""
    resp = await _upload(client, admin_headers, content=b"")
    assert resp.status_code == 400
    assert "不能为空" in resp.json()["message"]


@pytest.mark.asyncio
async def test_upload_disallowed_extension(client, admin_headers):
    """非法扩展名（.exe）→ 400。"""
    resp = await _upload(client, admin_headers, filename="evil.exe", content=b"MZ\x90")
    assert resp.status_code == 400
    assert "不支持的文件类型" in resp.json()["message"]


@pytest.mark.asyncio
async def test_upload_over_limit(client, admin_headers, tmp_path):
    """超大小 → 400（monkeypatch 上限调小）。"""
    import app.services.upload as upload_service

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(settings, "UPLOAD_MAX_SIZE", 10)
    monkeypatch.setattr(upload_service.settings, "UPLOAD_MAX_SIZE", 10)

    resp = await _upload(client, admin_headers, content=PNG_BYTES * 2)
    monkeypatch.undo()
    assert resp.status_code == 400
    assert "文件大小不能超过" in resp.json()["message"]


@pytest.mark.asyncio
async def test_upload_requires_login(client):
    """未登录 → 401。"""
    resp = await _upload(client, {})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_upload_prevents_path_traversal(client, admin_headers, tmp_path):
    """恶意文件名（../）→ 落盘为 UUID 文件名，URL 不含用户输入。"""
    import app.services.upload as upload_service

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    monkeypatch.setattr(upload_service.settings, "UPLOAD_DIR", str(tmp_path))

    resp = await _upload(client, admin_headers, filename="../../evil.png")
    monkeypatch.undo()
    assert resp.status_code in (200, 201)
    data = resp.json()["data"]
    assert ".." not in data["url"]
    # 目录外不应产生文件
    assert not (tmp_path.parent / "evil.png").exists()
