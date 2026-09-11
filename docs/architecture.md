# 架构设计说明

## 总体架构

```
浏览器 (Vue3 SPA)
    │  /api (Vite 代理 或 Nginx 反代)
    ▼
FastAPI (Uvicorn)
    ├── 中间件：请求ID → CORS → 请求日志
    ├── 认证：JWT Access/Refresh 双 Token
    ├── 权限：RBAC 依赖注入
    ├── Service 层：业务逻辑
    └── 数据层：SQLAlchemy 2.0 异步 ORM
         ├── PostgreSQL 15（主存储）
         └── Redis 7（Refresh Token / 黑名单 / 限流）
```

## 分层设计

- **Router (api/v1)**：参数校验、调用 Service、统一响应包装
- **Service**：业务逻辑（认证、RBAC 聚合、菜单树过滤），可独立单元测试
- **Model**：SQLAlchemy ORM，仅数据映射
- **Core**：配置、数据库、Redis、JWT、依赖注入、统一响应/异常、日志、限流

## 响应约定

统一格式 `{ code, message, data }`：

- 成功：`{"code": 0, "message": "ok", "data": ...}`
- 业务错误：`{"code": <http状态码>, "message": "错误描述", "data": null}`（同时返回对应 HTTP 状态码）

## 认证流程

1. 登录 → 校验密码 → 签发 Access(15min) + Refresh(7d)
2. Refresh Token 存 Redis：`app:auth:refresh:{user_id}`
3. 刷新：用 Refresh 换新 Token 对（旧 Refresh 失效，Token 轮换）
4. 登出：Refresh 从 Redis 删除，Access 加入黑名单 `app:auth:blacklist:{jti}`（TTL=剩余有效期）

## 权限模型

```
用户 ──<user_roles>── 角色 ──<role_permissions>── 权限 (code: "resource:action")
                        └──<role_menus>── 菜单（树形）
```

- 超管（is_superuser）跳过校验，权限码返回 `["*"]`
- 菜单可见性：`permission_code` 为空 → 登录即可见；否则需拥有对应权限
- 前端按钮级控制：`v-permission="'user:delete'"`

## 三种启动方式一致性

- 所有配置经环境变量注入（`pydantic-settings`），无硬编码
- `.env` 与 Docker 环境变量加载逻辑统一
- Alembic 迁移与初始化脚本在所有模式下均可执行
