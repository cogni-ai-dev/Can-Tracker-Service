import hashlib
import hmac
import secrets

from argon2 import PasswordHasher, Type, exceptions
from pydantic import SecretStr

SESSION_TOKEN_BYTES = 32
_PASSWORD_HASHER = PasswordHasher(type=Type.ID)


def secret_is_configured(secret: SecretStr | None) -> bool:
    return bool(secret and secret.get_secret_value())


def hash_password(password: str) -> str:
    if not password:
        raise ValueError("Password must not be empty.")
    return _PASSWORD_HASHER.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _PASSWORD_HASHER.verify(password_hash, password)
    except (exceptions.VerificationError, exceptions.InvalidHashError):
        return False


def new_session_token() -> str:
    return secrets.token_urlsafe(SESSION_TOKEN_BYTES)


def hash_session_token(token: str, secret_key: SecretStr) -> str:
    return hmac.new(
        secret_key.get_secret_value().encode("utf-8"),
        token.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
