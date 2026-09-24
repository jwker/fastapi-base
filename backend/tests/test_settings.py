"""生产环境安全护栏测试：prod 下默认 SECRET_KEY / 初始超管密码必须拒绝启动。"""

import pytest

from app.core.config import Settings


def test_prod_rejects_default_secret_key(monkeypatch):
    """prod + 默认 SECRET_KEY → 拒绝启动。"""
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("SECRET_KEY", "change-me-in-production")
    monkeypatch.setenv("INIT_ADMIN_PASSWORD", "a-strong-password-123")
    with pytest.raises(ValueError, match="SECRET_KEY"):
        Settings()


def test_prod_rejects_default_admin_password(monkeypatch):
    """prod + 默认初始密码 admin123 → 拒绝启动。"""
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("SECRET_KEY", "a-strong-random-secret-key-0123456789")
    monkeypatch.setenv("INIT_ADMIN_PASSWORD", "admin123")
    with pytest.raises(ValueError, match="初始超管密码"):
        Settings()


def test_prod_passes_when_configured(monkeypatch):
    """prod + 已改密钥与密码 → 正常构造。"""
    monkeypatch.setenv("APP_ENV", "prod")
    monkeypatch.setenv("SECRET_KEY", "a-strong-random-secret-key-0123456789")
    monkeypatch.setenv("INIT_ADMIN_PASSWORD", "a-strong-password-123")
    s = Settings()
    assert s.is_prod


def test_non_prod_allows_defaults(monkeypatch):
    """test/dev 环境不拦截默认值（现有测试与本地开发不受影响）。"""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key-0123456789-0123456789")
    monkeypatch.setenv("INIT_ADMIN_PASSWORD", "admin123")
    s = Settings()
    assert not s.is_prod


def test_cors_derived_from_frontend_port(monkeypatch):
    """未显式配置 ALLOWED_ORIGINS 时，CORS 由根 .env 的 FRONTEND_PORT 派生。"""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    s = Settings()
    assert s.FRONTEND_PORT == 5173
    assert s.cors_origins == [f"http://localhost:{s.FRONTEND_PORT}"]


def test_cors_explicit_override(monkeypatch):
    """显式配置 ALLOWED_ORIGINS 时优先使用显式值。"""
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("ALLOWED_ORIGINS", "https://example.com,http://localhost:9000")
    s = Settings()
    assert s.cors_origins == ["https://example.com", "http://localhost:9000"]
