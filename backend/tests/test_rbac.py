"""用户/角色/菜单/权限 CRUD 与 RBAC 测试。"""

import pytest


@pytest.mark.asyncio
async def test_create_user_and_list(client, admin_headers):
    resp = await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": "alice", "password": "alice123", "nickname": "爱丽丝"},
    )
    assert resp.status_code in (200, 201)
    assert resp.json()["data"]["username"] == "alice"

    resp = await client.get("/api/v1/users?page=1&page_size=10", headers=admin_headers)
    assert resp.status_code in (200, 201)
    assert resp.json()["data"]["total"] >= 1


@pytest.mark.asyncio
async def test_create_duplicate_user(client, admin_headers):
    payload = {"username": "bob", "password": "bob12345"}
    await client.post("/api/v1/users", headers=admin_headers, json=payload)
    resp = await client.post("/api/v1/users", headers=admin_headers, json=payload)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_delete_user(client, admin_headers):
    created = await client.post(
        "/api/v1/users", headers=admin_headers, json={"username": "carol", "password": "carol123"}
    )
    user_id = created.json()["data"]["id"]
    resp = await client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)
    assert resp.status_code in (200, 201)

    resp = await client.delete(f"/api/v1/users/{user_id}", headers=admin_headers)
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_cannot_delete_superuser(client, admin_headers, admin_user):
    resp = await client.delete(f"/api/v1/users/{admin_user.id}", headers=admin_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_role_crud(client, admin_headers):
    resp = await client.post(
        "/api/v1/roles",
        headers=admin_headers,
        json={"name": "审计员", "code": "auditor", "description": "只读审计"},
    )
    assert resp.status_code in (200, 201)
    role_id = resp.json()["data"]["id"]

    resp = await client.get(f"/api/v1/roles/{role_id}", headers=admin_headers)
    assert resp.status_code in (200, 201)
    assert resp.json()["data"]["code"] == "auditor"

    resp = await client.put(
        f"/api/v1/roles/{role_id}", headers=admin_headers, json={"description": "更新"}
    )
    assert resp.json()["data"]["description"] == "更新"

    resp = await client.delete(f"/api/v1/roles/{role_id}", headers=admin_headers)
    assert resp.status_code in (200, 201)


@pytest.mark.asyncio
async def test_builtin_role_not_deletable(client, admin_headers):
    roles = (await client.get("/api/v1/roles", headers=admin_headers)).json()["data"]["items"]
    super_admin = next(r for r in roles if r["code"] == "super_admin")
    resp = await client.delete(f"/api/v1/roles/{super_admin['id']}", headers=admin_headers)
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_permissions_list(client, admin_headers):
    resp = await client.get("/api/v1/permissions", headers=admin_headers)
    assert resp.status_code in (200, 201)
    codes = [p["code"] for p in resp.json()["data"]["items"]]
    assert "user:create" in codes
    assert "menu:delete" in codes


@pytest.mark.asyncio
async def test_menu_tree_and_crud(client, admin_headers):
    # 种子菜单树
    resp = await client.get("/api/v1/menus/tree", headers=admin_headers)
    assert resp.status_code in (200, 201)
    tree = resp.json()["data"]
    assert len(tree) >= 2

    # 创建
    resp = await client.post(
        "/api/v1/menus",
        headers=admin_headers,
        json={"name": "报表", "path": "/reports", "component": "ReportList", "icon": "DataLine"},
    )
    assert resp.status_code in (200, 201)
    menu_id = resp.json()["data"]["id"]

    # 更新
    resp = await client.put(
        f"/api/v1/menus/{menu_id}", headers=admin_headers, json={"sort_order": 99}
    )
    assert resp.json()["data"]["sort_order"] == 99

    # 删除
    resp = await client.delete(f"/api/v1/menus/{menu_id}", headers=admin_headers)
    assert resp.status_code in (200, 201)


@pytest.mark.asyncio
async def test_rbac_forbidden(client, admin_headers):
    """普通用户无 user:create 权限 → 403。"""
    # 创建普通用户并分配 user 角色
    created = await client.post(
        "/api/v1/users", headers=admin_headers, json={"username": "lily", "password": "lily123"}
    )
    user_id = created.json()["data"]["id"]

    roles = (await client.get("/api/v1/roles", headers=admin_headers)).json()["data"]["items"]
    user_role = next(r for r in roles if r["code"] == "user")
    await client.put(
        f"/api/v1/users/{user_id}", headers=admin_headers, json={"role_ids": [user_role["id"]]}
    )

    login = await client.post(
        "/api/v1/auth/login", json={"username": "lily", "password": "lily123"}
    )
    lily_headers = {"Authorization": f"Bearer {login.json()['data']['tokens']['access_token']}"}

    # 只读 OK
    resp = await client.get("/api/v1/users", headers=lily_headers)
    assert resp.status_code in (200, 201)

    # 写操作 403
    resp = await client.post(
        "/api/v1/users", headers=lily_headers, json={"username": "x", "password": "xxxxxx"}
    )
    assert resp.status_code == 403

    resp = await client.post(
        "/api/v1/menus", headers=lily_headers, json={"name": "x", "path": "/x"}
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_user_menus_filtered_by_permission(client, admin_headers):
    """普通用户菜单树中，无权限的子菜单被过滤。"""
    created = await client.post(
        "/api/v1/users", headers=admin_headers, json={"username": "tom", "password": "tom123"}
    )
    user_id = created.json()["data"]["id"]
    roles = (await client.get("/api/v1/roles", headers=admin_headers)).json()["data"]["items"]
    user_role = next(r for r in roles if r["code"] == "user")
    await client.put(
        f"/api/v1/users/{user_id}", headers=admin_headers, json={"role_ids": [user_role["id"]]}
    )

    login = await client.post("/api/v1/auth/login", json={"username": "tom", "password": "tom123"})
    headers = {"Authorization": f"Bearer {login.json()['data']['tokens']['access_token']}"}

    resp = await client.get("/api/v1/menus/my", headers=headers)
    assert resp.status_code in (200, 201)
    tree = resp.json()["data"]
    # 用户有 user:read/role:read/menu:read/permission:read → 系统管理下所有子菜单都可见
    system = next(m for m in tree if m["path"] == "/system")
    assert len(system["children"]) >= 2


@pytest.mark.asyncio
async def test_menu_tree_no_duplicate_children(client, admin_headers):
    """菜单树子节点不得重复（build_tree 与 selectin 填充冲突回归）。"""
    resp = await client.get("/api/v1/menus/my", headers=admin_headers)
    assert resp.status_code in (200, 201)
    tree = resp.json()["data"]

    def count(nodes):
        total = len(nodes)
        for n in nodes:
            total += count(n.get("children", []))
        return total

    # 种子数据：2 根 + 5 子 = 7（含操作日志菜单）；重复则 > 7
    assert count(tree) == 7


@pytest.mark.asyncio
async def test_stats_overview_superuser_only(client, admin_headers):
    """统计接口仅超管可访问：超管 200，普通用户 403。"""
    # 超管可访问
    resp = await client.get("/api/v1/stats/overview", headers=admin_headers)
    assert resp.status_code in (200, 201)
    data = resp.json()["data"]
    assert "user_count" in data
    assert "menu_count" in data

    # 普通用户 403
    await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": "stats_user", "password": "stats123"},
    )
    login = await client.post(
        "/api/v1/auth/login", json={"username": "stats_user", "password": "stats123"}
    )
    headers = {"Authorization": f"Bearer {login.json()['data']['tokens']['access_token']}"}
    resp = await client.get("/api/v1/stats/overview", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["code"] == 403


@pytest.mark.asyncio
async def test_menu_visibility_follows_role_menu_assignment(client, admin_headers):
    """角色只分配了「用户管理」菜单时，用户菜单树只含该菜单及其父级。"""
    # 1. 找到用户管理菜单 id
    tree = (await client.get("/api/v1/menus/tree", headers=admin_headers)).json()["data"]
    users_menu_id = None
    system_menu_id = None
    for m in tree:
        if m["path"] == "/system":
            system_menu_id = m["id"]
        for c in m.get("children", []):
            if c["path"] == "/users":
                users_menu_id = c["id"]
    assert users_menu_id and system_menu_id

    # 2. 创建角色并分配权限 + 仅「用户管理」菜单
    role = (
        await client.post(
            "/api/v1/roles",
            headers=admin_headers,
            json={"name": "仅用户管理", "code": "only_users"},
        )
    ).json()["data"]
    role_id = role["id"]
    perms = (await client.get("/api/v1/permissions?page_size=200", headers=admin_headers)).json()[
        "data"
    ]["items"]
    user_read = next(p["id"] for p in perms if p["code"] == "user:read")
    await client.put(
        f"/api/v1/roles/{role_id}/permissions",
        headers=admin_headers,
        json={"permission_ids": [user_read]},
    )
    await client.put(
        f"/api/v1/roles/{role_id}/menus",
        headers=admin_headers,
        json={"menu_ids": [users_menu_id]},
    )

    # 3. 创建用户并挂该角色
    await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": "limited", "password": "limited123", "role_ids": [role_id]},
    )

    # 4. 登录查看菜单
    login = await client.post(
        "/api/v1/auth/login", json={"username": "limited", "password": "limited123"}
    )
    headers = {"Authorization": f"Bearer {login.json()['data']['tokens']['access_token']}"}
    resp = await client.get("/api/v1/menus/my", headers=headers)
    assert resp.status_code in (200, 201)
    my_tree = resp.json()["data"]

    # 系统管理（容器）+ 用户管理，且不含角色/权限/菜单管理
    paths = set()
    for m in my_tree:
        paths.add(m["path"])
        paths.update(c["path"] for c in m.get("children", []))
    assert "/system" in paths
    assert "/users" in paths
    assert "/roles" not in paths
    assert "/permissions" not in paths
    assert "/menus" not in paths
    assert "/dashboard" not in paths  # 未分配则不可见


@pytest.mark.asyncio
async def test_empty_container_menu_hidden(client, admin_headers):
    """角色只分配父菜单、未分配任何子菜单时，父菜单整体隐藏（无空下拉）。"""
    tree = (await client.get("/api/v1/menus/tree", headers=admin_headers)).json()["data"]
    system_menu_id = next(m["id"] for m in tree if m["path"] == "/system")

    role = (
        await client.post(
            "/api/v1/roles",
            headers=admin_headers,
            json={"name": "空容器", "code": "empty_container"},
        )
    ).json()["data"]
    # 只分配父菜单「系统管理」，不分配任何子菜单
    await client.put(
        f"/api/v1/roles/{role['id']}/menus",
        headers=admin_headers,
        json={"menu_ids": [system_menu_id]},
    )
    await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={
            "username": "emptyuser",
            "password": "emptyuser1",
            "role_ids": [role["id"]],
        },
    )

    login = await client.post(
        "/api/v1/auth/login", json={"username": "emptyuser", "password": "emptyuser1"}
    )
    headers = {"Authorization": f"Bearer {login.json()['data']['tokens']['access_token']}"}
    resp = await client.get("/api/v1/menus/my", headers=headers)
    assert resp.status_code in (200, 201)
    # 没有任何可见菜单（父级因无子菜单被剪除）
    assert resp.json()["data"] == []


@pytest.mark.asyncio
async def test_three_level_menu_tree(client, admin_headers):
    """三级菜单：分配最深层叶子 → 祖先链补全完整显示；空中间容器被剪除。"""
    # 建三级结构：业务中心(Layout) > 订单(Layout) > 订单列表(页面)
    biz = (
        await client.post(
            "/api/v1/menus",
            headers=admin_headers,
            json={"name": "业务中心", "path": "/biz", "component": "Layout"},
        )
    ).json()["data"]
    orders = (
        await client.post(
            "/api/v1/menus",
            headers=admin_headers,
            json={"name": "订单", "path": "/orders", "component": "Layout", "parent_id": biz["id"]},
        )
    ).json()["data"]
    order_list = (
        await client.post(
            "/api/v1/menus",
            headers=admin_headers,
            json={
                "name": "订单列表",
                "path": "/orders/list",
                "component": "OrderList",
                "parent_id": orders["id"],
            },
        )
    ).json()["data"]

    # 角色只分配最深层叶子
    role = (
        await client.post(
            "/api/v1/roles",
            headers=admin_headers,
            json={"name": "三层验证", "code": "three_level"},
        )
    ).json()["data"]
    await client.put(
        f"/api/v1/roles/{role['id']}/menus",
        headers=admin_headers,
        json={"menu_ids": [order_list["id"]]},
    )
    await client.post(
        "/api/v1/users",
        headers=admin_headers,
        json={"username": "threeuser", "password": "threeuser1", "role_ids": [role["id"]]},
    )

    login = await client.post(
        "/api/v1/auth/login", json={"username": "threeuser", "password": "threeuser1"}
    )
    headers = {"Authorization": f"Bearer {login.json()['data']['tokens']['access_token']}"}
    resp = await client.get("/api/v1/menus/my", headers=headers)
    assert resp.status_code in (200, 201)
    tree = resp.json()["data"]

    # 业务中心 > 订单 > 订单列表，完整三级（祖先自动补全）
    assert len(tree) == 1 and tree[0]["path"] == "/biz"
    assert len(tree[0]["children"]) == 1 and tree[0]["children"][0]["path"] == "/orders"
    leaf = tree[0]["children"][0]["children"]
    assert len(leaf) == 1 and leaf[0]["path"] == "/orders/list"

    # 清理
    await client.delete(f"/api/v1/menus/{order_list['id']}", headers=admin_headers)
    await client.delete(f"/api/v1/menus/{orders['id']}", headers=admin_headers)
    await client.delete(f"/api/v1/menus/{biz['id']}", headers=admin_headers)


@pytest.mark.asyncio
async def test_update_user_avatar(client, admin_headers):
    """管理员更新用户头像：UserUpdate 支持 avatar，返回与列表一致。"""
    created = await client.post(
        "/api/v1/users", headers=admin_headers, json={"username": "av_usr", "password": "av12345"}
    )
    user_id = created.json()["data"]["id"]
    # 创建时头像默认空
    assert created.json()["data"]["avatar"] == ""

    resp = await client.put(
        f"/api/v1/users/{user_id}",
        headers=admin_headers,
        json={"avatar": "/uploads/202609/abc.png"},
    )
    assert resp.status_code in (200, 201)
    assert resp.json()["data"]["avatar"] == "/uploads/202609/abc.png"

    # 列表返回也带 avatar
    listed = await client.get("/api/v1/users", headers=admin_headers)
    item = next(u for u in listed.json()["data"]["items"] if u["id"] == user_id)
    assert item["avatar"] == "/uploads/202609/abc.png"
