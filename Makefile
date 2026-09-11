# FastAPI Base 脚手架 - 常用命令
.PHONY: help install dev-backend dev-frontend check test lint format migrate init-db \
	up down build logs clean

help: ## 显示帮助
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'

install: ## 安装后端(uv)与前端(pnpm)依赖
	cd backend && uv sync
	cd frontend && pnpm install

dev-backend: ## 启动后端开发服务(热重载)
	cd backend && PYTHONPATH=. uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

dev-frontend: ## 启动前端开发服务
	cd frontend && pnpm dev

check: ## 本地完整自检（与 GitHub CI 命令链一致，提交前必跑）
	cd backend && uv run ruff check app tests scripts
	cd backend && uv run ruff format --check app tests scripts
	cd backend && PYTHONPATH=. uv run pytest
	cd frontend && pnpm lint
	cd frontend && pnpm test
	cd frontend && pnpm build

test: ## 运行后端测试
	cd backend && PYTHONPATH=. uv run pytest

lint: ## 代码检查(ruff + vue-tsc)
	cd backend && uv run ruff check app tests scripts
	cd frontend && pnpm build

format: ## 代码格式化
	cd backend && uv run ruff format app tests scripts

migrate: ## 执行数据库迁移
	cd backend && uv run alembic upgrade head

init-db: ## 初始化权限/角色/超管/菜单数据
	cd backend && PYTHONPATH=. uv run python scripts/init_db.py

up: ## Docker 一键启动全部服务
	docker compose up -d --build

down: ## 停止并移除容器
	docker compose down

build: ## 构建镜像
	docker compose build

logs: ## 查看容器日志
	docker compose logs -f

clean: ## 清理本地数据与缓存
	rm -rf backend/data backend/logs backend/.venv backend/.pytest_cache
	rm -rf frontend/dist frontend/node_modules
