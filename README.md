# FastAPI Base 全栈脚手架

基于 **FastAPI + Vue 3** 的前后端分离脚手架，内置 JWT 双 Token 认证、RBAC 权限、动态菜单路由，支持三种启动方式（纯本地 / 混合 / 全 Docker）。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | FastAPI 0.115+ · SQLAlchemy 2.0 (async) · PostgreSQL 15 · Redis 7 · Alembic · UV |
| 认证 | JWT 双 Token（Access 15min + Refresh 7d 存 Redis）+ 登出黑名单 |
| 权限 | RBAC：用户 → 角色 → 权限 / 菜单，FastAPI 依赖注入校验 |
| 前端 | Vue 3.5 · Vite · TypeScript · Element Plus · Pinia · Vue Router · Axios |
| 部署 | Docker Compose · Nginx（SPA + Gzip + 反向代理） |

## 快速开始

### 环境要求

- Docker + Docker Compose（推荐）
- 或本地安装：Python 3.12+、Node.js 22+、pnpm、UV、PostgreSQL 15+、Redis 7+

### 方式一：Docker 整体启动（推荐）

```bash
cp .env.example .env          # 按需修改（默认超管 admin/admin123）
docker compose up -d --build
```

- 前端：http://localhost:5173
- 后端 API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/health

### 方式二：Docker 运行依赖 + 本地代码（混合模式）

```bash
# 只启动数据库与 Redis
docker compose up -d db redis

cd backend
cp .env.example .env
# 修改 .env：DATABASE_URL=postgresql+asyncpg://fastapi:fastapi@localhost:5432/fastapi
uv sync
uv run alembic upgrade head
PYTHONPATH=. uv run python scripts/init_db.py
PYTHONPATH=. uv run uvicorn app.main:app --reload --port 8000

cd ../frontend
cp .env.example .env        # 可选：默认值开箱即用
pnpm install
pnpm dev   # http://localhost:5173，/api 自动代理到 8000
```

### 方式三：完全本地启动（无 Docker）

```bash
# 需要本地 PostgreSQL 与 Redis
cd backend
cp .env.example .env          # 按需修改 DATABASE_URL / REDIS_URL
uv sync && uv run alembic upgrade head
PYTHONPATH=. uv run python scripts/init_db.py
PYTHONPATH=. uv run uvicorn app.main:app --reload --port 8000

cd ../frontend
cp .env.example .env        # 可选：默认值开箱即用
pnpm install && pnpm dev
```

> 前端 `.env` 不复制也能直接跑（代码内置默认值），按需自定义时才需要。

> 本地无 PostgreSQL 时，可将 `DATABASE_URL` 改为 `sqlite+aiosqlite:///./data/app.db`（脚手架默认），
> Redis 缺失时登录/刷新接口不可用，其余接口不受影响。

## 环境变量

### 后端 `backend/.env`

| 变量 | 说明 | 默认 |
| --- | --- | --- |
| `APP_ENV` | dev / test / prod | dev |
| `SECRET_KEY` | JWT 签名密钥（生产必改，≥32 字节） | change-me-in-production |
| `DATABASE_URL` | 数据库连接串 | sqlite+aiosqlite:///./data/app.db |
| `REDIS_URL` | Redis 连接串 | redis://localhost:6379/0 |
| `ALLOWED_ORIGINS` | CORS 白名单（逗号分隔） | http://localhost:5173 |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access Token 有效期 | 15 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh Token 有效期 | 7 |
| `RATE_LIMIT_PER_MINUTE` | 限流阈值 | 60 |
| `INIT_ADMIN_USERNAME/PASSWORD` | 初始超管 | admin / admin123 |
| `SENTRY_DSN` | Sentry 上报（可选） | 空 |

### 前端 `frontend/.env`

| 变量 | 说明 | 默认 |
| --- | --- | --- |
| `VITE_APP_TITLE` | 应用标题 | FastAPI Base |
| `VITE_API_BASE_URL` | API 基础路径 | /api |

## 默认账号

| 账号 | 密码 | 角色 |
| --- | --- | --- |
| admin | admin123 | 超级管理员（全部权限） |

## 常用命令

```bash
make dev-backend    # 后端热重载
make dev-frontend   # 前端开发
make test           # 后端测试
make e2e            # 前端 E2E（Playwright，需后端 8000 与前端 5173 已启动）
make migrate        # 数据库迁移
make init-db        # 初始化数据（幂等）
make up             # Docker 一键启动
```

详见 [docs/deployment.md](docs/deployment.md) 部署文档。

## 目录结构

```
.
├── backend/               # FastAPI 后端
│   ├── app/
│   │   ├── core/          # 配置/数据库/Redis/认证/依赖/响应/日志/限流
│   │   ├── models/        # SQLAlchemy 模型（user/role/permission/menu）
│   │   ├── schemas/       # Pydantic 模型
│   │   ├── services/      # 业务逻辑层
│   │   ├── api/v1/        # 路由（auth/users/roles/permissions/menus）
│   │   ├── middleware/    # 请求ID/日志中间件
│   │   └── main.py        # 应用入口
│   ├── alembic/           # 数据库迁移
│   ├── scripts/init_db.py # 数据初始化
│   └── tests/             # pytest 测试
├── frontend/              # Vue3 前端
│   ├── src/
│   │   ├── api/           # 接口封装
│   │   ├── router/        # 固定路由 + 动态路由生成
│   │   ├── stores/        # Pinia（user/permission/app）
│   │   ├── directives/    # v-permission
│   │   ├── components/    # ProTable 通用表格
│   │   ├── layouts/       # 布局（侧边栏/顶栏）
│   │   └── views/         # 页面
│   └── nginx.conf         # SPA 部署配置
├── docker-compose.yml     # 一键编排
└── Makefile
```

## 贡献指南

- 分支：`main`（生产） / `develop`（开发） / `feature/*` / `hotfix/*`
- 提交遵循 [Conventional Commits](https://www.conventionalcommits.org/)：`feat:` `fix:` `docs:` `refactor:` `test:` `chore:` 等
- 后端代码：Ruff 格式化与检查，类型注解完整
- 前端代码：ESLint + Prettier，组件 PascalCase
- PR 流程：从 `develop` 切功能分支 → 开发 → 测试 → PR 合入 `develop` → 发布时合入 `main`

## API 文档

- Swagger UI：`http://localhost:8000/docs`
- ReDoc：`http://localhost:8000/redoc`
- 健康检查：`GET /health`
- 指标：`GET /metrics`（Prometheus）
