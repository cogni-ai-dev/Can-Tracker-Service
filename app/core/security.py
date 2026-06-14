from pydantic import SecretStr


def secret_is_configured(secret: SecretStr | None) -> bool:
    return bool(secret and secret.get_secret_value())
