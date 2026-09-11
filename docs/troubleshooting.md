# 常见问题排查

## 后端

### 1. 登录报 500 / ConnectionRefusedError
Redis 未启动。Refresh Token 存储在 Redis：
```bash
docker compose up -d redis   # 或用本地 redis-server
```

### 2. `MissingGreenlet: greenlet_spawn has not been called`
在异步上下文外触发了 ORM lazy load。检查：
- 查询是否缺少 `selectinload`（如 `Menu.children`）
- 是否在 `db.commit()` 后访问未加载的 relationship
- 集合赋值前对象是否已被 autoflush 变为 persistent（可用 `db.no_autoflush`）

### 3. 迁移失败
```bash
cd backend
rm -rf data && uv run alembic upgrade head
PYTHONPATH=. uv run python scripts/init_db.py
```

### 4. bcrypt 报 72 字节错误
已弃用 passlib，使用 bcrypt 直接调用（`app/core/security.py`），密码最长 72 字节。

### 5. 端口被占用
```bash
lsof -i :8000 && kill <pid>
```

## 前端

### 1. `Cannot find module '@/xxx'`
tsconfig.app.json 的 `paths` 未配置或未重启编辑器。检查 `"@/*": ["./src/*"]`。

### 2. 登录后空白 / 路由不渲染
- 动态路由未注册：检查 `permissionStore.routesLoaded` 流程
- 菜单 `component` 与 `src/views/` 文件名不匹配（组件映射表解析失败）
- 刷新页面后菜单重新拉取，若后端菜单树为空则无路由

### 3. 暗色主题失效
`main.ts` 中 `appStore.applyTheme()` 需在 mount 前调用；检查 `html.dark` 类是否存在。

### 4. 代理 502
后端未启动或端口不一致：vite.config.ts `target` 默认 `http://localhost:8000`，可用 `VITE_PROXY_TARGET` 覆盖。

### 5. pnpm 构建报 ignored build scripts
确认 `pnpm-workspace.yaml` 已配置 `allowBuilds`，且 Dockerfile 复制了该文件。

## Docker

### 1. 端口冲突（5432/6379/5173）
`.env` 中修改 `POSTGRES_PORT` / `REDIS_PORT` / `FRONTEND_PORT`。

### 2. 容器名冲突
```bash
docker rm -f fb-db fb-redis fb-backend fb-frontend
docker compose up -d
```

### 3. backend 容器反复重启
```bash
docker compose logs backend   # 查看迁移/初始化错误
```

## 数据库

### 1. 菜单树子节点重复
升级代码后重启 backend 容器（`docker compose up -d --build backend`）。

### 2. 重置数据
```bash
# 开发环境
docker compose down -v   # 删除 volume 全部重置
# 或仅清库
docker compose exec db psql -U fastapi -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"
```
