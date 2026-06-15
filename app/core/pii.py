import base64
import hashlib
import hmac
import os
import re
from dataclasses import dataclass

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from pydantic import SecretStr

from app.core.config import Settings, get_settings

PII_CIPHERTEXT_PREFIX = "pii:v1"
PII_NONCE_BYTES = 12

PAN_FIELD = "pan"
MOBILE_FIELD = "mobile"
EMAIL_FIELD = "email"
BANK_ACCOUNT_NUMBER_FIELD = "bank_account_number"
PASSWORD_FIELD = "password"

SENSITIVE_PII_FIELDS = frozenset(
    {
        PAN_FIELD,
        MOBILE_FIELD,
        EMAIL_FIELD,
        BANK_ACCOUNT_NUMBER_FIELD,
    }
)

AUDIT_REDACTED_FIELDS = frozenset(
    {
        PASSWORD_FIELD,
        "password_hash",
        "session_token",
        "session_token_hash",
    }
)

PAN_PATTERN = re.compile(r"\s+")
NON_DIGIT_PATTERN = re.compile(r"\D+")


@dataclass(frozen=True)
class ProtectedPII:
    ciphertext: str | None
    masked: str | None
    search_hash: str | None


def _settings(settings: Settings | None) -> Settings:
    return settings or get_settings()


def _secret_value(secret: SecretStr | None, setting_name: str) -> str:
    if secret is None or not secret.get_secret_value():
        raise RuntimeError(f"{setting_name} is required.")
    return secret.get_secret_value()


def _derive_aes_key(secret: SecretStr | None) -> bytes:
    return hashlib.sha256(_secret_value(secret, "PII_ENCRYPTION_KEY").encode()).digest()


def _hash_key(secret: SecretStr | None) -> bytes:
    return _secret_value(secret, "PII_SEARCH_HASH_KEY").encode()


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode((value + padding).encode("ascii"))


def normalize_pii_value(field_name: str, value: object | None) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    if not normalized:
        return None

    if field_name == PAN_FIELD:
        return PAN_PATTERN.sub("", normalized).upper()
    if field_name == MOBILE_FIELD:
        digits = NON_DIGIT_PATTERN.sub("", normalized)
        return digits or normalized
    if field_name == EMAIL_FIELD:
        return normalized.lower()
    if field_name == BANK_ACCOUNT_NUMBER_FIELD:
        return PAN_PATTERN.sub("", normalized).upper()
    return normalized


def encrypt_pii_value(field_name: str, value: object | None, settings: Settings | None = None) -> str | None:
    normalized = normalize_pii_value(field_name, value)
    if normalized is None:
        return None

    nonce = os.urandom(PII_NONCE_BYTES)
    aesgcm = AESGCM(_derive_aes_key(_settings(settings).pii_encryption_key))
    ciphertext = aesgcm.encrypt(
        nonce,
        normalized.encode(),
        associated_data=field_name.encode(),
    )
    return f"{PII_CIPHERTEXT_PREFIX}:{_b64encode(nonce)}:{_b64encode(ciphertext)}"


def decrypt_pii_value(field_name: str, ciphertext: str | None, settings: Settings | None = None) -> str | None:
    if ciphertext is None:
        return None
    parts = ciphertext.split(":")
    if len(parts) != 4 or ":".join(parts[:2]) != PII_CIPHERTEXT_PREFIX:
        raise ValueError("Unsupported PII ciphertext format.")

    nonce = _b64decode(parts[2])
    encrypted = _b64decode(parts[3])
    aesgcm = AESGCM(_derive_aes_key(_settings(settings).pii_encryption_key))
    plaintext = aesgcm.decrypt(
        nonce,
        encrypted,
        associated_data=field_name.encode(),
    )
    return plaintext.decode("utf-8")


def pii_search_hash(field_name: str, value: object | None, settings: Settings | None = None) -> str | None:
    normalized = normalize_pii_value(field_name, value)
    if normalized is None:
        return None
    return hmac.new(
        _hash_key(_settings(settings).pii_search_hash_key),
        f"{field_name}:{normalized}".encode(),
        hashlib.sha256,
    ).hexdigest()


def _mask_middle(value: str, *, prefix: int, suffix: int) -> str:
    if len(value) <= prefix + suffix:
        if len(value) <= 1:
            return "*"
        return value[:prefix] + ("*" * max(len(value) - prefix, 0))
    tail = value[-suffix:] if suffix else ""
    return value[:prefix] + ("*" * (len(value) - prefix - suffix)) + tail


def mask_pan(value: object | None) -> str | None:
    normalized = normalize_pii_value(PAN_FIELD, value)
    if normalized is None:
        return None
    if len(normalized) >= 10:
        return normalized[:5] + ("*" * (len(normalized) - 6)) + normalized[-1]
    return _mask_middle(normalized, prefix=1, suffix=1)


def mask_mobile(value: object | None) -> str | None:
    normalized = normalize_pii_value(MOBILE_FIELD, value)
    if normalized is None:
        return None
    if len(normalized) <= 4:
        return "*" * len(normalized)
    return ("*" * (len(normalized) - 4)) + normalized[-4:]


def mask_email(value: object | None) -> str | None:
    normalized = normalize_pii_value(EMAIL_FIELD, value)
    if normalized is None:
        return None

    local_part, separator, domain = normalized.partition("@")
    if not separator:
        return _mask_middle(normalized, prefix=1, suffix=1)

    masked_local = _mask_middle(local_part, prefix=1, suffix=0)
    domain_parts = domain.split(".")
    if domain_parts and domain_parts[0]:
        domain_parts[0] = _mask_middle(domain_parts[0], prefix=1, suffix=0)
    return f"{masked_local}@{'.'.join(domain_parts)}"


def mask_bank_account_number(value: object | None) -> str | None:
    normalized = normalize_pii_value(BANK_ACCOUNT_NUMBER_FIELD, value)
    if normalized is None:
        return None
    return f"bank account ending {normalized[-4:].rjust(4, '*')}"


def mask_pii_value(field_name: str, value: object | None) -> str | None:
    if field_name == PAN_FIELD:
        return mask_pan(value)
    if field_name == MOBILE_FIELD:
        return mask_mobile(value)
    if field_name == EMAIL_FIELD:
        return mask_email(value)
    if field_name == BANK_ACCOUNT_NUMBER_FIELD:
        return mask_bank_account_number(value)
    if field_name in AUDIT_REDACTED_FIELDS:
        return "[REDACTED]" if value is not None else None
    return None if value is None else str(value)


def protect_pii_value(field_name: str, value: object | None, settings: Settings | None = None) -> ProtectedPII:
    normalized = normalize_pii_value(field_name, value)
    if normalized is None:
        return ProtectedPII(ciphertext=None, masked=None, search_hash=None)
    return ProtectedPII(
        ciphertext=encrypt_pii_value(field_name, normalized, settings),
        masked=mask_pii_value(field_name, normalized),
        search_hash=pii_search_hash(field_name, normalized, settings),
    )


def encrypt_pan(value: object | None, settings: Settings | None = None) -> str | None:
    return encrypt_pii_value(PAN_FIELD, value, settings)


def encrypt_mobile(value: object | None, settings: Settings | None = None) -> str | None:
    return encrypt_pii_value(MOBILE_FIELD, value, settings)


def encrypt_email(value: object | None, settings: Settings | None = None) -> str | None:
    return encrypt_pii_value(EMAIL_FIELD, value, settings)


def encrypt_bank_account_number(value: object | None, settings: Settings | None = None) -> str | None:
    return encrypt_pii_value(BANK_ACCOUNT_NUMBER_FIELD, value, settings)


def pan_search_hash(value: object | None, settings: Settings | None = None) -> str | None:
    return pii_search_hash(PAN_FIELD, value, settings)


def mobile_search_hash(value: object | None, settings: Settings | None = None) -> str | None:
    return pii_search_hash(MOBILE_FIELD, value, settings)


def email_search_hash(value: object | None, settings: Settings | None = None) -> str | None:
    return pii_search_hash(EMAIL_FIELD, value, settings)


def bank_account_number_search_hash(value: object | None, settings: Settings | None = None) -> str | None:
    return pii_search_hash(BANK_ACCOUNT_NUMBER_FIELD, value, settings)


def protect_pan(value: object | None, settings: Settings | None = None) -> ProtectedPII:
    return protect_pii_value(PAN_FIELD, value, settings)


def protect_mobile(value: object | None, settings: Settings | None = None) -> ProtectedPII:
    return protect_pii_value(MOBILE_FIELD, value, settings)


def protect_email(value: object | None, settings: Settings | None = None) -> ProtectedPII:
    return protect_pii_value(EMAIL_FIELD, value, settings)


def protect_bank_account_number(value: object | None, settings: Settings | None = None) -> ProtectedPII:
    return protect_pii_value(BANK_ACCOUNT_NUMBER_FIELD, value, settings)
