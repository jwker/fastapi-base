"""应用配置：pydantic-settings，优先级 环境变量 > .env > 默认值。"""

from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # 本地 backend/.env 优先，根 .env 补充（FRONTEND_PORT 等跨层键的唯一源）
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # 应用
    APP_NAME: str = "FastAPI Base"
    APP_ENV: str = "dev"  # dev | test | prod
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"
    SECRET_KEY: str = "change-me-in-production"
    # 前端 dev 端口（唯一事实源在根 .env 的 FRONTEND_PORT；CORS 默认由它派生）
    FRONTEND_PORT: int = 5173
    # 显式 CORS 白名单（逗号分隔）；为空时由 FRONTEND_PORT 派生 http://localhost:<port>
    ALLOWED_ORIGINS: str = ""

    # 数据库
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/app.db"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # JWT
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    # 限流
    RATE_LIMIT_PER_MINUTE: int = 60

    # 登录失败锁定（RuoYi 同款默认：5 次 / 10 分钟，Redis 计数滑动窗口）
    LOGIN_FAIL_LIMIT: int = 5
    LOGIN_LOCK_MINUTES: int = 10

    # 初始化
    INIT_ADMIN_USERNAME: str = "admin"
    INIT_ADMIN_PASSWORD: str = "admin123"

    # 文件上传
    UPLOAD_DIR: str = "uploads"
    UPLOAD_MAX_SIZE: int = 5 * 1024 * 1024  # 5MB
    UPLOAD_ALLOWED_EXTENSIONS: str = "jpg,jpeg,png,gif,webp,svg,pdf,doc,docx,xls,xlsx"

    # 监控
    SENTRY_DSN: str = ""

    @property
    def cors_origins(self) -> list[str]:
        if self.ALLOWED_ORIGINS.strip():
            return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]
        # 未显式配置时，跟随前端 dev 端口（改根 .env FRONTEND_PORT 一处即可）
        return [f"http://localhost:{self.FRONTEND_PORT}"]

    @property
    def is_prod(self) -> bool:
        return self.APP_ENV == "prod"

    @property
    def upload_allowed_ext_set(self) -> set[str]:
        """上传允许的扩展名集合（小写、不含点）。"""
        return {e.strip().lower() for e in self.UPLOAD_ALLOWED_EXTENSIONS.split(",") if e.strip()}

    @model_validator(mode="after")
    def _validate_prod_security(self):
        """生产环境安全护栏：默认密钥/密码拒绝启动（fail-fast），dev/test 不拦截。"""
        if self.is_prod:
            if self.SECRET_KEY in (
                "change-me-in-production",
                "change-me-to-a-random-32+bytes-string",
            ):
                raise ValueError(
                    "生产环境（APP_ENV=prod）必须设置随机 SECRET_KEY（在 .env 中配置），拒绝启动"
                )
            if self.INIT_ADMIN_PASSWORD == "admin123":
                raise ValueError(
                    "生产环境（APP_ENV=prod）必须修改初始超管密码 INIT_ADMIN_PASSWORD，拒绝启动"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
