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
