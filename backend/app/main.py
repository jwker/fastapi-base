"""FastAPI 应用入口。"""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi.errors import RateLimitExceeded

from app.api.v1 import (
    audit_logs,
    auth,
    configs,
    dicts,
    files,
    menus,
    permissions,
    roles,
    stats,
    users,
)
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.response import AppError, app_error_handler, success
from app.middleware.audit import AuditMiddleware
from app.middleware.log import RequestLogMiddleware
from app.middleware.request_id import RequestIDMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    if settings.SENTRY_DSN:
        import sentry_sdk

        sentry_sdk.init(dsn=settings.SENTRY_DSN, environment=settings.APP_ENV)
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# 中间件（后添加的先执行，故顺序：Audit → RequestID → CORS → Log）
# Audit 置于最外层：覆盖所有写请求，旁路缓存 body，不影响业务读取
app.add_middleware(AuditMiddleware)
app.add_middleware(RequestLogMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)

# 统一异常
app.add_exception_handler(AppError, app_error_handler)


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(_: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429, content={"code": 429, "message": "请求过于频繁", "data": None}
    )


# 路由
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(users.router, prefix=settings.API_V1_PREFIX)
app.include_router(roles.router, prefix=settings.API_V1_PREFIX)
app.include_router(permissions.router, prefix=settings.API_V1_PREFIX)
app.include_router(menus.router, prefix=settings.API_V1_PREFIX)
app.include_router(stats.router, prefix=settings.API_V1_PREFIX)
app.include_router(audit_logs.router, prefix=settings.API_V1_PREFIX)
app.include_router(files.router, prefix=settings.API_V1_PREFIX)
app.include_router(dicts.router, prefix=settings.API_V1_PREFIX)
app.include_router(configs.router, prefix=settings.API_V1_PREFIX)


# 上传文件静态访问（开发直连 FastAPI；生产由 Nginx 托管 uploads 共享卷，不走 Python）
Path(settings.UPLOAD_DIR).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")


@app.get("/health", tags=["系统"])
async def health():
    return success({"status": "ok"})


@app.get("/", tags=["系统"])
async def root():
    return success({"app": settings.APP_NAME, "docs": "/docs"})


# Prometheus 指标
Instrumentator().instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)
