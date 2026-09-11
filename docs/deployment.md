# 部署说明

## 生产环境部署

### 1. 准备

```bash
git clone <repo> && cd fastapi-base
cp .env.example .env
# 必须修改：
#   SECRET_KEY（≥32 字节随机串，如 openssl rand -hex 32）
#   INIT_ADMIN_PASSWORD（初始超管密码）
#   ALLOWED_ORIGINS（真实域名）
#   SENTRY_DSN（如需错误追踪）
```

### 2. 构建与启动

```bash
docker compose up -d --build
```

### 3. 验证

```bash
curl http://localhost:8000/health          # {"code":0,...}
curl -I http://localhost:5173/             # 前端 200
```

## 前端 Nginx 说明（frontend/nginx.conf）

- SPA 路由：`try_files $uri $uri/ /index.html`
- `/api/` 反向代理到 backend 容器
- Gzip 压缩与静态资源 30 天缓存

## 后端容器说明

- 启动命令自动执行：`alembic upgrade head` → `init_db.py`（幂等）→ `uvicorn`
- 生产环境 `APP_ENV=prod`：日志以 JSON 格式输出到 `/app/logs/app.log`，按 20MB 轮转、保留 30 天
- 生产关闭 SQL echo，限流默认 60 次/分钟

## 数据库备份

```bash
# PostgreSQL
docker exec fb-db pg_dump -U fastapi fastapi > backup.sql

# 恢复
docker exec -i fb-db psql -U fastapi fastapi < backup.sql
```

## HTTPS（推荐反代方案）

生产建议在 Nginx 前再加一层网关（如 Caddy / Nginx / 云负载均衡）终结 TLS：

```nginx
server {
    listen 443 ssl;
    server_name your-domain.com;
    ssl_certificate     /path/cert.pem;
    ssl_certificate_key /path/key.pem;

    location / {
        proxy_pass http://127.0.0.1:5173;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 升级迁移流程

1. 修改模型 → `uv run alembic revision --autogenerate -m "描述"`
2. 测试环境验证：`uv run alembic upgrade head`
3. 备份生产库
4. 生产执行：`docker compose exec backend alembic upgrade head`
5. 滚动重启 backend 容器

## 监控

- Prometheus 指标：`http://localhost:8000/metrics`
- 健康检查：`GET /health`（可接入负载均衡探活）
- 错误追踪：配置 `SENTRY_DSN` 后自动上报

## 常见问题

| 问题 | 排查 |
| --- | --- |
| 前端 502 | `docker compose logs backend`，多为数据库未就绪或迁移失败 |
| 登录 401 | Redis 未启动（Refresh Token 存储依赖） |
| 端口冲突 | `docker compose down` 后调整 `.env` 中端口 |
