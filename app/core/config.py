import json
from functools import lru_cache
from urllib.parse import urlparse

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
    backup_retention_days: int = Field(default=14, alias="BACKUP_RETENTION_DAYS")

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
        if self.app_env == "production":
            self._validate_production_settings()
        return self

    def _validate_production_settings(self) -> None:
        if self.database_url and (
            not self.database_url.startswith("postgresql")
            or any(token in self.database_url.lower() for token in ("<", "placeholder", "replace-with"))
        ):
            raise ValueError("DATABASE_URL must use PostgreSQL and must not contain placeholders in production.")
        cors_origins = self.cors_origin_list
        if not cors_origins:
            raise ValueError("CORS_ORIGINS must be configured in production.")
        for origin in cors_origins:
            parsed_origin = urlparse(origin)
            if (
                origin == "*"
                or any(token in origin.lower() for token in ("<", "placeholder", "replace-with", "localhost"))
                or parsed_origin.scheme != "https"
                or not parsed_origin.netloc
            ):
                raise ValueError("CORS_ORIGINS must contain only concrete HTTPS production origins.")
        if self.backup_retention_days < 14:
            raise ValueError("BACKUP_RETENTION_DAYS must be at least 14 in production.")

        secret_values: list[str] = []
        for env_name, value in (
            ("APP_SECRET_KEY", self.app_secret_key),
            ("PII_ENCRYPTION_KEY", self.pii_encryption_key),
            ("PII_SEARCH_HASH_KEY", self.pii_search_hash_key),
        ):
            secret_value = value.get_secret_value() if value is not None else ""
            secret_values.append(secret_value)
            normalized = secret_value.lower()
            if (
                len(secret_value) < 32
                or "change-me" in normalized
                or "placeholder" in normalized
                or "replace-with" in normalized
                or normalized.startswith("<")
            ):
                raise ValueError(f"{env_name} must be a non-placeholder value of at least 32 characters in production.")
        if len(set(secret_values)) != len(secret_values):
            raise ValueError("APP_SECRET_KEY, PII_ENCRYPTION_KEY, and PII_SEARCH_HASH_KEY must be independent values.")

    @field_validator("session_ttl_seconds")
    @classmethod
    def validate_session_ttl_seconds(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("SESSION_TTL_SECONDS must be greater than zero.")
        return value

    @field_validator("backup_retention_days")
    @classmethod
    def validate_backup_retention_days(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("BACKUP_RETENTION_DAYS must be greater than zero.")
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

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
