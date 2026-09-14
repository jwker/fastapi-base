"""应用配置：pydantic-settings，优先级 环境变量 > .env > 默认值。"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
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
    ALLOWED_ORIGINS: str = "http://localhost:5173"

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
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def is_prod(self) -> bool:
        return self.APP_ENV == "prod"

    @property
    def upload_allowed_ext_set(self) -> set[str]:
        """上传允许的扩展名集合（小写、不含点）。"""
        return {e.strip().lower() for e in self.UPLOAD_ALLOWED_EXTENSIONS.split(",") if e.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
