import json
from functools import lru_cache

from pydantic import Field, SecretStr, ValidationInfo, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_env: str = Field(default="test", alias="APP_ENV")
    app_secret_key: SecretStr | None = Field(default=None, alias="APP_SECRET_KEY")
    database_url: str | None = Field(default=None, alias="DATABASE_URL")
    pii_encryption_key: SecretStr | None = Field(default=None, alias="PII_ENCRYPTION_KEY")
    pii_search_hash_key: SecretStr | None = Field(default=None, alias="PII_SEARCH_HASH_KEY")
    session_cookie_name: str = Field(default="can_tracker_session", alias="SESSION_COOKIE_NAME")
    session_cookie_secure: bool = Field(default=False, alias="SESSION_COOKIE_SECURE")
    session_ttl_seconds: int = Field(default=8 * 60 * 60, alias="SESSION_TTL_SECONDS")
    cors_origins: str = Field(default="", alias="CORS_ORIGINS")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("app_env", "log_level")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("cors_origins", mode="before")
    @classmethod
    def normalize_cors_origins(cls, value: object, info: ValidationInfo) -> str:
        if value is None:
            return ""
        if isinstance(value, list):
            return ",".join(str(item) for item in value)
        if isinstance(value, str):
            return value.strip()
        raise TypeError(f"{info.field_name} must be a comma-separated string or list of origins.")

    @model_validator(mode="after")
    def apply_test_defaults_and_validate_required_settings(self) -> "Settings":
        self.app_env = self.app_env.lower()
        self.log_level = self.log_level.upper()

        if self.app_env == "test":
            self.app_secret_key = self.app_secret_key or SecretStr("test-app-secret-key")
            self.database_url = self.database_url or "sqlite+pysqlite:///:memory:"
            self.pii_encryption_key = self.pii_encryption_key or SecretStr("test-pii-encryption-key")
            self.pii_search_hash_key = self.pii_search_hash_key or SecretStr("test-pii-search-hash-key")
            return self

        missing = [
            env_name
            for env_name, value in (
                ("APP_SECRET_KEY", self.app_secret_key),
                ("DATABASE_URL", self.database_url),
                ("PII_ENCRYPTION_KEY", self.pii_encryption_key),
                ("PII_SEARCH_HASH_KEY", self.pii_search_hash_key),
            )
            if not value
        ]
        if missing:
            joined = ", ".join(missing)
            raise ValueError(f"Missing required settings outside test mode: {joined}")
        if self.app_env not in {"local", "dev", "development"} and not self.session_cookie_secure:
            raise ValueError("SESSION_COOKIE_SECURE must be true outside local and test environments.")
        return self

    @field_validator("session_ttl_seconds")
    @classmethod
    def validate_session_ttl_seconds(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("SESSION_TTL_SECONDS must be greater than zero.")
        return value

    @property
    def cors_origin_list(self) -> list[str]:
        raw = self.cors_origins.strip()
        if not raw:
            return []
        if raw.startswith("["):
            parsed = json.loads(raw)
            if not isinstance(parsed, list):
                raise ValueError("CORS_ORIGINS JSON value must be a list.")
            return [str(origin).strip() for origin in parsed if str(origin).strip()]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def is_test(self) -> bool:
        return self.app_env == "test"


@lru_cache
def get_settings() -> Settings:
    return Settings()
