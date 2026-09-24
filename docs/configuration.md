# 配置说明

本文档说明项目的全部配置：环境变量文件职责、每个键的含义与默认值、配置读取链路、不同运行模式下哪些配置生效，以及常见修改操作。

## 1. 配置体系总览

项目使用三份 `.env` 文件 + Docker Compose 变量，各司其职：

| 文件 | 职责 | 谁读它 |
| --- | --- | --- |
| **根 `.env`** | 端口唯一事实源 + 混合模式连接串 + Compose 变量 | Docker Compose、后端 Settings（`../.env`）、vite.config.ts（loadEnv）、playwright.config.ts（fs 读取） |
| **`backend/.env`** | 后端特有键（应用/安全/Token/限流/初始化） | 后端 Settings（`.env`，优先级高于根） |
| **`frontend/.env`** | 前端业务变量（VITE_*） | vite.config.ts（loadEnv）、浏览器构建 |
| **`docker-compose.yml`** | 容器形态的环境变量（写死容器内连接串与运行参数） | 容器进程 |

读取优先级（后端）：**环境变量 > `backend/.env` > 根 `.env` > 代码默认值**。

## 2. 根 `.env`（唯一事实源）

### 端口组

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `BACKEND_PORT` | 8000 | 后端 API 端口（唯一事实源）。跟随：本地 `make dev-backend`、vite dev 代理默认、Docker 宿主映射 |
| `FRONTEND_PORT` | 5173 | 前端 dev 端口（唯一事实源）。跟随：vite dev 端口、后端 CORS 派生、Docker 宿主映射、本地 E2E baseURL |
| `POSTGRES_PORT` | 5433 | db 容器宿主映射端口（容器内固定 5432），宿主机冲突时才改 |
| `REDIS_PORT` | 6380 | redis 容器宿主映射端口（容器内固定 6379），宿主机冲突时才改 |

### 连接串组（混合模式用）

| 变量 | 说明 |
| --- | --- |
| `DATABASE_URL` | 数据库连接串。**混合模式（本地跑后端）时生效**；全 Docker 时被 compose 注入的容器内连接串（`@db:5432`）覆盖，不生效 |
| `REDIS_URL` | Redis 连接串。同上，全 Docker 时被 `redis://redis:6379/0` 覆盖 |

### 中间件与安全组

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `POSTGRES_USER` / `POSTGRES_PASSWORD` / `POSTGRES_DB` | fastapi | db 容器账号/密码/库名，Compose 使用 |
| `SECRET_KEY` | change-me-in-production-0123456789 | JWT 签名密钥（Compose 注入；本地后端实际用 backend/.env 的同名键，见 §3） |
| `ALLOWED_ORIGINS` | 空（派生） | CORS 显式白名单（逗号分隔，可选）；不设时后端自动派生 `http://localhost:{FRONTEND_PORT}` |

### 初始化与监控组

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `INIT_ADMIN_USERNAME` / `INIT_ADMIN_PASSWORD` | admin / admin123 | 初始超管账号（Compose 注入；本地后端用 backend/.env 的同名键） |
| `SENTRY_DSN` | 空 | Sentry 上报（可选） |

## 3. `backend/.env`（后端特有键）

> `DATABASE_URL` / `REDIS_URL` 已统一移至根 `.env`，**不要在此重复设置**。

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `APP_NAME` | FastAPI Base | 应用名 |
| `APP_ENV` | dev | dev / test / prod（prod 触发安全护栏：默认密钥/密码拒绝启动） |
| `DEBUG` | true | 调试模式 |
| `SECRET_KEY` | change-me-to-a-random-32+bytes-string | JWT 签名密钥（**本地/混合模式实际生效值**，优先级高于根 .env） |
| `ALLOWED_ORIGINS` | 注释 | 可选显式覆盖 CORS（不设时由根 .env 的 FRONTEND_PORT 派生） |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 15 | Access Token 有效期 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | 7 | Refresh Token 有效期（存 Redis） |
| `RATE_LIMIT_PER_MINUTE` | 60 | 接口限流阈值 |
| `INIT_ADMIN_USERNAME` / `INIT_ADMIN_PASSWORD` | admin / admin123 | 初始超管（初始化脚本用） |
| `SENTRY_DSN` | 空 | Sentry 上报（可选） |

## 4. `frontend/.env`（前端业务变量）

| 变量 | 默认 | 说明 |
| --- | --- | --- |
| `VITE_APP_TITLE` | FastAPI Base | 浏览器标签标题 |
| `VITE_API_BASE_URL` | /api/v1 | API 基础路径（业务代码 import.meta.env 用） |
| `VITE_PROXY_TARGET` | 注释 | dev 代理目标，**可选覆盖**；默认跟随根 .env 的 `BACKEND_PORT`（`http://localhost:<port>`），仅当后端不在本机（如远程/容器）时设置 |

> vite dev 端口不由本文件控制，由根 `.env` 的 `FRONTEND_PORT` 统一控制。

## 5. 配置读取链路

```
根 .env ──┬─→ Docker Compose（端口映射 + 容器环境变量）
          ├─→ 后端 Settings（config.py env_file=(".env", "../.env")，backend/.env 优先）
          ├─→ vite.config.ts（loadEnv 读根目录，port/proxy 默认）
          └─→ playwright.config.ts（fs 读 FRONTEND_PORT，E2E baseURL 默认）

backend/.env ──→ 后端 Settings（.env 优先于根，后端特有键）
frontend/.env ──→ vite.config.ts（loadEnv 合并，frontend 覆盖根）+ 浏览器构建
Makefile ──→ PORT 默认读根 .env BACKEND_PORT（命令行 PORT=8011 可临时覆盖）
```

## 6. 运行模式与配置生效关系

| 模式 | 后端在哪 | 数据库/Redis 连接 | 生效的配置 |
| --- | --- | --- | --- |
| **全 Docker**（`docker compose up`） | 容器 | compose 注入容器内连接串（`@db:5432`、`redis://redis:6379/0`） | 根 .env 的端口/凭据 + compose 写死环境变量；backend/.env 与 frontend/.env 不生效 |
| **混合**（compose 起 db/redis + 本地后端） | 宿主机 | 根 .env 的 `DATABASE_URL` / `REDIS_URL`（指向宿主映射端口） | 根 .env 连接串 + backend/.env 特有键 + frontend/.env |
| **完全本地**（无 Docker） | 宿主机 | 根 .env 的 `DATABASE_URL` / `REDIS_URL`（指向本机自装服务） | 同上 |

## 7. 常见操作

1. **改后端端口**：只改根 `.env` 的 `BACKEND_PORT`；临时覆盖用 `make dev-backend PORT=8011`
2. **改前端端口**：只改根 `.env` 的 `FRONTEND_PORT`（dev/CORS/Docker 映射/E2E 自动跟随）；临时覆盖用 `pnpm dev --port 5174`
3. **改中间件宿主端口**：根 `.env` 的 `POSTGRES_PORT` / `REDIS_PORT`；**改后需同步根 `.env` 的 `DATABASE_URL` / `REDIS_URL` 端口**
4. **改连接串**：根 `.env` 的 `DATABASE_URL` / `REDIS_URL`（混合/本地模式）
5. **改 CORS**：默认无需改（跟随 FRONTEND_PORT）；显式覆盖设根 `.env` 或 backend/.env 的 `ALLOWED_ORIGINS`
6. **改密钥/超管密码**：生产环境必须改根 `.env` 与 backend/.env 的 `SECRET_KEY`、`INIT_ADMIN_PASSWORD`（prod 护栏会拒绝默认值启动）
7. **新增环境变量**：按消费方选择位置——Compose/多端共享 → 根 `.env`；仅后端 → `backend/.env`；仅前端浏览器可见 → `frontend/.env`（VITE_ 前缀）

## 8. 安全注意

- `.env`（根、backend、frontend）均在 `.gitignore` 中，不入库；**`.env.example` 是模板，严禁写入真实凭据**
- 前端 `VITE_*` 变量会进浏览器 bundle，**不要放密钥**；`SECRET_KEY`、数据库密码等只放后端可读的 .env
- 生产环境（APP_ENV=prod）有安全护栏：`SECRET_KEY` / `INIT_ADMIN_PASSWORD` 为默认值时拒绝启动
