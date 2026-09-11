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

    # 监控
    SENTRY_DSN: str = ""

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",") if o.strip()]

    @property
    def is_prod(self) -> bool:
        return self.APP_ENV == "prod"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
