# 测试说明

本仓库的测试体系分三层：**后端单元/接口测试（pytest）→ 前端单元/组件测试（Vitest）→ 端到端测试（Playwright）**，并由 GitHub Actions CI 统一把关。本文档覆盖：测试体系总览、各层如何运行、覆盖范围清单、如何新增测试、已知问题与踩坑记录。

---

## 1. 测试体系总览

```
┌─────────────────────────────────────────────────────────────┐
│  GitHub Actions CI（每次 push / PR 自动触发，4 个 job）        │
│  Backend(lint+test) · Frontend(lint+test+build) · E2E · Docker │
└─────────────────────────────────────────────────────────────┘
        ▲                        ▲                        ▲
        │ make check             │ pnpm e2e               │ 提交前门禁
┌───────┴────────┐      ┌────────┴────────┐      ┌────────┴────────┐
│ 后端 pytest    │      │ 前端 Vitest     │      │ 前端 Playwright │
│ 79 例 / 8 文件 │      │ 97 例 / 18 文件 │      │ 6 例 / 3 文件   │
│ 单元+接口      │      │ 组件/Store/工具 │      │ 真浏览器主链路  │
└────────────────┘      └─────────────────┘      └─────────────────┘
```

| 层 | 框架 | 数量 | 运行耗时（约） | 覆盖重点 |
|---|---|---|---|---|
| 后端测试 | pytest + pytest-asyncio | 79 例 | 10-20s | 认证/权限/CRUD/日志/上传/导出 |
| 前端测试 | Vitest + jsdom | 97 例 | 10s | 组件/Store/路由/工具/页面 |
| 端到端测试 | Playwright (chromium) | 6 例 | 6-10s | 登录/菜单/权限/登出主链路 |

**三者分工**：后端测接口与业务规则；前端测组件与状态逻辑；E2E 测"真实浏览器 + 真实后端"的整条主链路（单测覆盖不到的时序、路由守卫联动、权限指令）。

---

## 2. 技术栈与配置位置

| 项 | 技术 | 配置位置 |
|---|---|---|
| 后端测试 | pytest、pytest-asyncio（asyncio_mode=auto）、httpx（ASGI 客户端） | `backend/pyproject.toml`（`[tool.pytest.ini_options]`） |
| 后端测试基建 | `backend/tests/conftest.py`（SQLite 内存库、FakeRedis、fixtures） | — |
| 前端测试 | Vitest（jsdom 环境、globals） | `frontend/vitest.config.ts` |
| E2E | `@playwright/test`（chromium） | `frontend/playwright.config.ts`、`frontend/e2e/` |
| CI 门禁 | GitHub Actions | `.github/workflows/ci.yml` |
| 本地一键自检 | Makefile `check` / `test` / `e2e` | `Makefile` |

> 前端 `vitest.config.ts` 显式排除了 `e2e/**`：Playwright 用例与 Vitest 共用 `*.spec.ts` 后缀，若不排除，`pnpm test` 会把 E2E 文件当单测跑而报错。

---

## 3. 后端测试（pytest · 79 例）

### 3.1 运行方式

```bash
cd backend
PYTHONPATH=. uv run pytest          # 全量
PYTHONPATH=. uv run pytest tests/test_auth.py -k "login"   # 过滤单个
```

或从仓库根目录：`make test`。

### 3.2 测试基建（conftest.py）

后端测试**不需要外部依赖**，全部在内存中完成：

- **SQLite 内存数据库**（`setup_db`，autouse）：每个测试自动建表、测试结束清空，测试间完全隔离；
- **FakeRedis**（`fake_redis`，autouse）：用内存实现替换真实 Redis，覆盖 `get/set/setex/delete/incr/expire/ttl/eval`——登录锁定计数、token 黑名单等 Redis 逻辑无需真实 Redis 即可测试；
- **常用 fixtures**：`client`（httpx AsyncClient，直连 ASGI 应用）、`db`（会话）、`admin_user`（种子超管）、`admin_headers`（超管 Bearer 头）。

### 3.3 覆盖范围清单

| 文件 | 例数 | 覆盖内容 |
|---|---|---|
| `test_auth.py` | 22 | 健康检查、登录成功/密码错误/未知用户、登录失败锁定（5 次/10 分钟、超管豁免）、刷新 token、登出、/me、token 黑名单 |
| `test_rbac.py` | 17 | 用户 CRUD（含重复用户名/非法角色）、角色管理、权限校验、非超管访问控制 |
| `test_audit.py` | 9 | 操作日志自动记录（body 掩码）、查询鉴权（仅超管可读） |
| `test_audit_export.py` | 9 | 操作日志导出 CSV（内容/过滤/空数据/权限） |
| `test_dict.py` | 8 | 字典类型/字典项 CRUD、code 唯一性、级联删除 |
| `test_files.py` | 8 | 文件元数据记录、来源/备注、列表分页搜索、删除（记录+磁盘） |
| `test_upload.py` | 6 | 上传成功落盘、空文件、非法扩展名、未登录 401 |
| **合计** | **79** | — |

### 3.4 关键约定

- `asyncio_mode = "auto"`：异步测试函数无需手动 `@pytest.mark.asyncio`；
- 所有测试通过 `client` fixture 走真实 ASGI 应用（含中间件），属于**接口级测试**；
- 测试写入的数据只存在于内存库，跑完即毁，不会污染 `backend/data/` 的开发库。

---

## 4. 前端测试（Vitest · 18 文件 97 例）

### 4.1 运行方式

```bash
cd frontend
pnpm test                 # 全量（vitest run，单次）
pnpm exec vitest src/utils/__tests__/request.spec.ts   # 单文件
```

> `pnpm test` 是 CI 用的 `vitest run`（跑完退出）；本地开发可 `pnpm exec vitest`（watch 模式）。

### 4.2 测试约定

- 环境：`jsdom` + `globals: true`（`it/expect` 全局可用）；
- 目录：测试文件与被测模块同目录下的 `__tests__/`，命名 `<模块>.spec.ts`；
- 组件测试直接挂载真实组件（`@vue/test-utils`），Store 测试用真实 Pinia + 内存状态。

### 4.3 覆盖范围清单

| 目录 | 文件 | 例数 | 覆盖内容 |
|---|---|---|---|
| components | `ProForm.spec.ts` | 14 | 字段配置驱动渲染、必填星号、防线校验、事件 |
| components | `TagsView.spec.ts` | 8 | affix 标签、keep-alive 缓存名单、右键菜单、关闭逻辑 |
| components | `ProTable.spec.ts` | 6 | 自动拉数据、分页/搜索、loading、操作列 |
| components | `FileUpload.spec.ts` | 3 | 文件选择/URL 输入、上传调用与 v-model 回传 |
| views | `AuditLogList.spec.ts` | 7 | 日志列表、筛选查询、权限控制 |
| views | `FileManager.spec.ts` | 8 | 文件列表渲染、缩略图/图标、来源备注、删除 |
| views | `DictList.spec.ts` | 6 | 字典类型/项列表、新增、校验拦截 |
| views | `MenuList.spec.ts` | 4 | 菜单树渲染、ProForm 防线校验 |
| views | `RoleList.spec.ts` | 4 | 角色列表渲染、新增 |
| views | `Profile.spec.ts` | 3 | 资料表单、密码不一致拦截 |
| views | `Dashboard.spec.ts` | 2 | 超管/普通用户统计卡片差异 |
| views | `UserList.spec.ts` | 1+ | 用户列表渲染 |
| stores | `tags.spec.ts` | 9 | 标签增删、cachedViews、右键操作 |
| stores | `user.spec.ts` | 3 | refresh 并发去重、失败共享 |
| utils | `request.spec.ts` | 10 | token 携带、401 刷新重放、错误提示、超管豁免 |
| composables | `useDict.spec.ts` | 4 | 字典加载、模块级缓存 |
| directives | `permission.spec.ts` | 3 | v-permission 有权限保留/无权限移除 |
| router | `dynamic.spec.ts` | 2 | 菜单 → 路由树生成（顶级/分组） |
| **合计** | **18** | **97** | — |

---

## 5. 端到端测试（Playwright · 6 例）

E2E 覆盖单测测不到的**真实浏览器 + 真实后端**主链路：登录 → 动态路由/菜单 → 按钮权限 → 登出。

### 5.1 本地运行步骤

前置：后端（8000）与前端（5173）已启动，且后端已初始化种子数据（含 `admin/admin123`）。

```bash
# 终端 1：后端
cd backend && PYTHONPATH=. uv run uvicorn app.main:app --reload --port 8000
# 首次需先建表 + 种子：make migrate && make init-db

# 终端 2：前端
cd frontend && pnpm dev          # http://localhost:5173

# 终端 3：跑 E2E
cd frontend && pnpm e2e          # 或 make e2e
```

预期输出：`6 passed`。Playwright 使用独立的 chromium 实例，不影响你正在使用的浏览器。

### 5.2 CI 运行方式

CI 中 `E2E (Playwright)` job 的完整链路：

```
services 容器（postgres:15 + redis:7）
  → alembic 迁移 + init_db 种子
  → 裸跑 uvicorn（127.0.0.1:8000）
  → 前端 pnpm build（显式注入 VITE_API_BASE_URL=/api/v1）
  → vite preview（4173，走 /api 代理到 8000）
  → pnpm e2e（headless chromium，E2E_BASE_URL=http://localhost:4173）
```

### 5.3 用例清单

| 文件 | 用例 | 断言要点 |
|---|---|---|
| `auth.spec.ts` | 登录成功 | 跳转 /dashboard、仪表盘可见、`fb-user` localStorage 含 accessToken |
| `auth.spec.ts` | 登录失败 | 弹出"用户名或密码错误"、停留登录页（只错 1 次避免触发锁定） |
| `auth.spec.ts` | 登出 | 下拉 → 确认弹窗 → 回登录页、token 清空 |
| `menu.spec.ts` | 菜单完整加载 | 一级菜单可见、展开"系统管理"后子菜单可见 |
| `menu.spec.ts` | 进入用户管理 | 点击菜单 → /users → 表格与表头渲染 |
| `permission.spec.ts` | admin 按钮权限 | "新增用户"按钮可见可点、弹窗打开/关闭 |

### 5.4 前置与注意事项

- 第一版用例**只读不写库**（登录失败只用错 1 次），不会污染开发数据；
- 选择器用可读文本（placeholder / role / 文本），**不使用固定 sleep**，动画时序全部用显式断言（`toBeVisible` / `toHaveURL`）；
- 首次在本机跑 E2E 需下载 chromium；国内网络下用镜像源（见 §9.2）。

---

## 6. CI 集成

`.github/workflows/ci.yml` 在每次 push / PR 时运行 4 个 job：

| Job | 命令链 | 通过条件 |
|---|---|---|
| `Backend (lint + test)` | `uv sync` → `ruff check` → `ruff format --check` → `pytest` | 79 例全过 + 无 lint/格式错误 |
| `Frontend (lint + test + build)` | `pnpm install` → `eslint` → `vitest run` → `vue-tsc + vite build` | 97 例全过 + lint + 构建成功 |
| `E2E (Playwright)` | 见 §5.2 | 6 例全过 |
| `Docker Build` | `docker compose build`（依赖前两个 job） | 镜像可构建 |

本地提交前应跑 `make check`，其命令链与 CI 的 Backend + Frontend job 一致（含 build）。

---

## 7. 测试步骤速查（从零跑通）

```bash
# 1. 安装依赖
make install                     # backend: uv sync；frontend: pnpm install

# 2. 准备本地环境（后端 + 种子数据）
make migrate && make init-db     # 建表 + 权限/角色/超管/菜单种子

# 3. 单层测试
make test                        # 后端 pytest（79 例）
cd frontend && pnpm test         # 前端 vitest（97 例）

# 4. 端到端测试（需先起前后端）
make dev-backend &               # 终端 1
make dev-frontend &              # 终端 2
make e2e                         # 6 例

# 5. 提交前全量自检（与 CI 一致）
make check                       # ruff + pytest + eslint + vitest + build
```

---

## 8. 如何新增测试

### 8.1 后端（pytest）

```python
# backend/tests/test_xxx.py —— 复用 conftest fixtures，无需造基建
async def test_something(client, admin_headers, db):
    resp = await client.get("/api/v1/xxx", headers=admin_headers)
    assert resp.status_code == 200
```

约定：
- 文件放 `backend/tests/`，命名 `test_<模块>.py`；
- 需要管理员身份的接口用 `admin_headers`；需要登录的用 `client` + 登录换取 token；
- 若用到新的 Redis 命令，先扩展 `conftest.py` 的 `FakeRedis`（否则测试会报不支持）。

### 8.2 前端（Vitest）

```ts
// frontend/src/xxx/__tests__/Xxx.spec.ts
import { mount } from '@vue/test-utils'
import { describe, it, expect, vi } from 'vitest'
```

约定：测试文件放在被测模块的 `__tests__/` 下；组件测试用 `@vue/test-utils` 挂载；Store 测试用真实 Pinia。

### 8.3 E2E（Playwright）

```ts
// frontend/e2e/xxx.spec.ts
test('描述', async ({ page }) => {
  await page.goto('/login')
  // ... 用可读文本选择器 + 显式断言
})
```

约定：
- 写链路（新增/编辑/删除）建议使用**独立测试账号或随机前缀数据**，避免污染开发库；
- 登录辅助函数（`login` / `loginAdmin`）已抽到各 spec 顶部，直接复用；
- 新增用例后本地先跑通 `pnpm e2e`，再确认 CI 的 E2E job。

---

## 9. 已知问题与踩坑记录

1. **Vitest 误收 E2E 文件**：`vitest` 默认匹配 `**/*.spec.ts`，会把 `frontend/e2e/` 当单测跑导致 `make check` 挂。`vitest.config.ts` 已 `exclude: ['e2e/**', ...]`，**新增测试目录时注意同样问题**（jest/playwright 共用 spec 后缀是常态坑）。

2. **Playwright 浏览器下载慢/失败**：官方源在国内常卡住。用镜像：
   ```bash
   PLAYWRIGHT_DOWNLOAD_HOST=https://npmmirror.com/mirrors/playwright pnpm exec playwright install chromium
   ```

3. **CI 登录 404（API 前缀）**：后端统一挂载在 `/api/v1`，前端 `request.ts` 默认值已对齐 `/api/v1`。但 `.env` 被 gitignore，CI 上不存在——CI build 步骤已显式注入 `VITE_API_BASE_URL=/api/v1`。**新环境若自建 CI/部署，必须注入该变量**，否则所有 API 404。本地 `.env.example` 也写的是 `/api/v1`。

4. **E2E 交互细节**：
   - 侧边栏"系统管理"是折叠分组，子菜单要先点击展开再断言/点击；
   - 登出有三步：头像下拉 hover 展开 → 点击"退出登录" → ElMessageBox 确认弹窗点"确定"；
   - 登出后 `fb-user` 的 localStorage 是**保留 key、值清空**（`{"accessToken":"","userInfo":null}`），断言应检查 token 为空而非 key 为 null。

5. **FakeRedis 需同步扩展**：后端新增 Redis 命令（如 `incr`/`expire`/`ttl`）时，`conftest.py` 的 FakeRedis 必须同步实现，否则真实 Redis 逻辑无法被测试覆盖。

6. **E2E 与端口占用**：本地若 `vite preview` 或调试用后端残留进程占用 4173/8010 等端口，E2E 会连到旧进程导致误判。用 `lsof -nP -iTCP:<端口> -sTCP:LISTEN` 排查。

7. **测试隔离**：后端测试用内存 SQLite（自动清空）；E2E 第一版只读不写库。新增写链路 E2E 时遵守 §8.3 约定，不要污染开发数据。

---

## 10. 覆盖缺口与后续建议

- **E2E 写链路**：新增/编辑/删除用户等写操作未覆盖（第一版刻意只读，避免污染）；
- **E2E 普通用户权限**：目前只有超管 admin 的按钮权限用例，非超管的按钮隐藏/菜单裁剪待补；
- **覆盖率统计**：后端未接入 pytest-cov、前端未开 coverage 报告，可后续加入并在 CI 设置门槛；
- **E2E 截图/视觉回归、多浏览器（firefox/webkit）、移动端视口**：Playwright 原生支持，按需扩展；
- **CI 真库验证**：E2E 的 postgres 为每次全新容器，可考虑加入迁移回滚等数据库专项测试。

---

> 本文档随代码演进维护；新增测试层或变更测试命令时，请同步更新 §2 配置表与 §3-§5 数量统计。
