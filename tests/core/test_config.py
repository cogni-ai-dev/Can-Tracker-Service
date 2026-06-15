import pytest
from pydantic import ValidationError

from app.core.config import Settings

STRONG_SECRET = "x" * 32
STRONG_PII_SECRET = "y" * 32
STRONG_HASH_SECRET = "z" * 32


def test_test_environment_uses_safe_defaults() -> None:
    settings = Settings(app_env="test")

    assert settings.database_url == "sqlite+pysqlite:///:memory:"
    assert settings.session_cookie_name == "can_tracker_session"
    assert settings.session_cookie_secure is False
    assert settings.app_secret_key is not None
    assert settings.pii_encryption_key is not None
    assert settings.pii_search_hash_key is not None


def test_required_secret_settings_fail_outside_test_mode() -> None:
    with pytest.raises(ValidationError, match="APP_SECRET_KEY"):
        Settings(app_env="local", database_url="sqlite+pysqlite:///:memory:")


def test_non_test_settings_accept_required_environment_values() -> None:
    settings = Settings(
        app_env="local",
        app_secret_key="local-secret",
        database_url="postgresql+psycopg://user:pass@localhost:5432/can_tracker",
        pii_encryption_key="local-pii-encryption-key",
        pii_search_hash_key="local-pii-search-hash-key",
        cors_origins="http://127.0.0.1:8000, http://localhost:8000",
        log_level="debug",
    )

    assert settings.app_env == "local"
    assert settings.log_level == "DEBUG"
    assert settings.cors_origin_list == ["http://127.0.0.1:8000", "http://localhost:8000"]


def test_secure_session_cookies_are_required_outside_local_and_test() -> None:
    with pytest.raises(ValidationError, match="SESSION_COOKIE_SECURE"):
        Settings(
            app_env="production",
            app_secret_key=STRONG_SECRET,
            database_url="postgresql+psycopg://user:pass@localhost:5432/can_tracker",
            pii_encryption_key=STRONG_PII_SECRET,
            pii_search_hash_key=STRONG_HASH_SECRET,
            session_cookie_secure=False,
            cors_origins="https://tracker.example.test",
        )


def test_production_settings_accept_secure_session_cookies() -> None:
    settings = Settings(
        app_env="production",
        app_secret_key=STRONG_SECRET,
        database_url="postgresql+psycopg://user:pass@localhost:5432/can_tracker",
        pii_encryption_key=STRONG_PII_SECRET,
        pii_search_hash_key=STRONG_HASH_SECRET,
        session_cookie_secure=True,
        cors_origins="https://tracker.example.test",
    )

    assert settings.session_cookie_secure is True


def test_production_settings_reject_placeholder_and_incomplete_values() -> None:
    with pytest.raises(ValidationError, match="APP_SECRET_KEY"):
        Settings(
            app_env="production",
            app_secret_key="change-me-production-secret-value",
            database_url="postgresql+psycopg://user:pass@localhost:5432/can_tracker",
            pii_encryption_key=STRONG_PII_SECRET,
            pii_search_hash_key=STRONG_HASH_SECRET,
            session_cookie_secure=True,
            cors_origins="https://tracker.example.test",
        )

    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(
            app_env="production",
            app_secret_key=STRONG_SECRET,
            database_url="sqlite+pysqlite:///prod.db",
            pii_encryption_key=STRONG_PII_SECRET,
            pii_search_hash_key=STRONG_HASH_SECRET,
            session_cookie_secure=True,
            cors_origins="https://tracker.example.test",
        )

    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(
            app_env="production",
            app_secret_key=STRONG_SECRET,
            database_url="postgresql+psycopg://user:pass@localhost:5432/can_tracker",
            pii_encryption_key=STRONG_PII_SECRET,
            pii_search_hash_key=STRONG_HASH_SECRET,
            session_cookie_secure=True,
        )

    with pytest.raises(ValidationError, match="BACKUP_RETENTION_DAYS"):
        Settings(
            app_env="production",
            app_secret_key=STRONG_SECRET,
            database_url="postgresql+psycopg://user:pass@localhost:5432/can_tracker",
            pii_encryption_key=STRONG_PII_SECRET,
            pii_search_hash_key=STRONG_HASH_SECRET,
            session_cookie_secure=True,
            cors_origins="https://tracker.example.test",
            backup_retention_days=7,
        )


def test_production_settings_reject_database_cors_and_secret_reuse_risks() -> None:
    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(
            app_env="production",
            app_secret_key=STRONG_SECRET,
            database_url="mysql://user:pass@db/can_tracker",
            pii_encryption_key=STRONG_PII_SECRET,
            pii_search_hash_key=STRONG_HASH_SECRET,
            session_cookie_secure=True,
            cors_origins="https://tracker.example.test",
        )

    with pytest.raises(ValidationError, match="DATABASE_URL"):
        Settings(
            app_env="production",
            app_secret_key=STRONG_SECRET,
            database_url="postgresql+psycopg://<postgres-user>:<postgres-password>@postgres:5432/<postgres-db>",
            pii_encryption_key=STRONG_PII_SECRET,
            pii_search_hash_key=STRONG_HASH_SECRET,
            session_cookie_secure=True,
            cors_origins="https://tracker.example.test",
        )

    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(
            app_env="production",
            app_secret_key=STRONG_SECRET,
            database_url="postgresql+psycopg://user:pass@localhost:5432/can_tracker",
            pii_encryption_key=STRONG_PII_SECRET,
            pii_search_hash_key=STRONG_HASH_SECRET,
            session_cookie_secure=True,
            cors_origins="*",
        )

    with pytest.raises(ValidationError, match="CORS_ORIGINS"):
        Settings(
            app_env="production",
            app_secret_key=STRONG_SECRET,
            database_url="postgresql+psycopg://user:pass@localhost:5432/can_tracker",
            pii_encryption_key=STRONG_PII_SECRET,
            pii_search_hash_key=STRONG_HASH_SECRET,
            session_cookie_secure=True,
            cors_origins="http://localhost:8000",
        )

    with pytest.raises(ValidationError, match="independent values"):
        Settings(
            app_env="production",
            app_secret_key=STRONG_SECRET,
            database_url="postgresql+psycopg://user:pass@localhost:5432/can_tracker",
            pii_encryption_key=STRONG_SECRET,
            pii_search_hash_key=STRONG_HASH_SECRET,
            session_cookie_secure=True,
            cors_origins="https://tracker.example.test",
        )
