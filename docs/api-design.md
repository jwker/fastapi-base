# API 设计规范

## 基础约定

- 前缀：`/api/v1`
- 响应统一：`{ "code": 0, "message": "ok", "data": ... }`
- 认证：`Authorization: Bearer <access_token>`
- 分页参数：`page`（默认 1）、`page_size`（默认 10，上限 100）
- 检索参数：`keyword`

## 接口清单

### 认证 /auth

| 方法 | 路径 | 说明 | 权限 |
| --- | --- | --- | --- |
| POST | /auth/login | 登录，返回 Token 对 + 用户信息 | 公开 |
| POST | /auth/refresh | 刷新 Token（Refresh 轮换） | 公开 |
| POST | /auth/logout | 登出（Refresh 删除 + Access 黑名单） | 登录 |
| GET | /auth/me | 当前用户信息（含权限/角色） | 登录 |

### 用户 /users

| 方法 | 路径 | 说明 | 权限 |
| --- | --- | --- | --- |
| GET | /users | 分页列表 | 登录 |
| GET | /users/{id} | 详情 | 登录 |
| POST | /users | 创建用户 | user:create |
| PUT | /users/{id} | 更新（含 role_ids） | user:update |
| DELETE | /users/{id} | 删除（超管不可删） | user:delete |

### 角色 /roles

| 方法 | 路径 | 说明 | 权限 |
| --- | --- | --- | --- |
| GET | /roles | 分页列表 | 登录 |
| GET | /roles/{id} | 详情 | 登录 |
| POST | /roles | 创建 | role:create |
| PUT | /roles/{id} | 更新 | role:update |
| PUT | /roles/{id}/permissions | 分配权限 | role:update |
| PUT | /roles/{id}/menus | 分配菜单 | role:update |
| DELETE | /roles/{id} | 删除（内置角色不可删） | role:delete |

### 权限 /permissions

| 方法 | 路径 | 说明 | 权限 |
| --- | --- | --- | --- |
| GET | /permissions | 分页列表 | permission:read |

### 菜单 /menus

| 方法 | 路径 | 说明 | 权限 |
| --- | --- | --- | --- |
| GET | /menus/tree | 全量菜单树（管理用） | 登录 |
| GET | /menus/my | 当前用户可见菜单树（动态路由用） | 登录 |
| POST | /menus | 创建 | menu:create |
| PUT | /menus/{id} | 更新 | menu:update |
| DELETE | /menus/{id} | 删除（级联子菜单） | menu:delete |

### 系统

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | /health | 健康检查 |
| GET | /metrics | Prometheus 指标 |
| GET | /docs | Swagger UI |

## 错误码约定

| code | 含义 |
| --- | --- |
| 0 | 成功 |
| 400 | 业务错误（参数/用户名密码错误等） |
| 401 | 未登录 / Token 失效 |
| 403 | 无权限（RBAC 拒绝） |
| 404 | 资源不存在 |
| 429 | 触发限流 |

## 状态码

- 成功统一 HTTP 200（创建资源也返回 200，业务码区分）
- 业务错误返回对应 HTTP 状态码（400/401/403/404/429/500）
