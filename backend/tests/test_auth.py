"""健康检查与认证流程测试。"""

import pytest


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["status"] == "ok"


@pytest.mark.asyncio
async def test_login_success(client, admin_user):
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["tokens"]["access_token"]
    assert data["tokens"]["refresh_token"]
    assert data["user"]["username"] == "admin"
    assert data["user"]["is_superuser"] is True


@pytest.mark.asyncio
async def test_login_wrong_password(client, admin_user):
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "wrong-pass"}
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == 400


@pytest.mark.asyncio
async def test_login_unknown_user(client):
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "nobody", "password": "whatever1"}
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_me_requires_token(client):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_success(client, admin_headers):
    resp = await client.get("/api/v1/auth/me", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["data"]["username"] == "admin"


@pytest.mark.asyncio
async def test_refresh_flow(client, admin_user):
    login = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    )
    refresh_token = login.json()["data"]["tokens"]["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["access_token"]
    assert data["refresh_token"] != refresh_token  # 轮换


@pytest.mark.asyncio
async def test_refresh_invalid(client):
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": "bad-token"})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout_blacklists_token(client, admin_user, fake_redis):
    login = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    )
    data = login.json()["data"]
    access = data["tokens"]["access_token"]
    refresh = data["tokens"]["refresh_token"]
    headers = {"Authorization": f"Bearer {access}"}

    resp = await client.post(
        "/api/v1/auth/logout", headers=headers, json={"refresh_token": refresh}
    )
    assert resp.status_code == 200

    # 登出后 access token 应失效
    resp = await client.get("/api/v1/auth/me", headers=headers)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_change_password_success(client, admin_headers):
    resp = await client.post(
        "/api/v1/auth/change-password",
        headers=admin_headers,
        json={"old_password": "admin123", "new_password": "newpass123"},
    )
    assert resp.status_code == 200

    # 新密码可登录
    login = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "newpass123"}
    )
    assert login.status_code == 200

    # 旧密码失效
    resp = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_change_password_wrong_old(client, admin_headers):
    resp = await client.post(
        "/api/v1/auth/change-password",
        headers=admin_headers,
        json={"old_password": "wrong-pass", "new_password": "newpass123"},
    )
    assert resp.status_code == 400
    assert resp.json()["code"] == 400


@pytest.mark.asyncio
async def test_change_password_same_as_old(client, admin_headers):
    resp = await client.post(
        "/api/v1/auth/change-password",
        headers=admin_headers,
        json={"old_password": "admin123", "new_password": "admin123"},
    )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_change_password_requires_auth(client):
    resp = await client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "admin123", "new_password": "newpass123"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_change_password_revokes_refresh(client, admin_user):
    login = await client.post(
        "/api/v1/auth/login", json={"username": "admin", "password": "admin123"}
    )
    refresh_token = login.json()["data"]["tokens"]["refresh_token"]
    access = login.json()["data"]["tokens"]["access_token"]

    resp = await client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {access}"},
        json={"old_password": "admin123", "new_password": "newpass123"},
    )
    assert resp.status_code == 200

    # 改密后旧 refresh token 失效
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_profile_update(client, admin_headers):
    resp = await client.put(
        "/api/v1/auth/profile",
        headers=admin_headers,
        json={"nickname": "新昵称", "email": "new@example.com", "phone": "13800000000"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["nickname"] == "新昵称"
    assert data["email"] == "new@example.com"
    assert data["phone"] == "13800000000"


@pytest.mark.asyncio
async def test_profile_update_ignores_privileged_fields(client, admin_headers):
    """尝试提交 username/status/is_superuser 等越权字段 → 被忽略。"""
    resp = await client.put(
        "/api/v1/auth/profile",
        headers=admin_headers,
        json={"username": "hacked", "status": 0, "is_superuser": False, "nickname": "正常昵称"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["username"] == "admin"  # 登录名未被篡改
    assert data["is_superuser"] is True  # 超管标志未被篡改
    assert data["nickname"] == "正常昵称"
