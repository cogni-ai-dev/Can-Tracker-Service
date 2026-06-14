import pytest
from pydantic import ValidationError

from app.core.config import Settings


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
