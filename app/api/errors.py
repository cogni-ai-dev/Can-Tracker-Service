from typing import Any

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import is_sensitive_key, redact_sensitive_data, redact_sensitive_text


class ApiError(Exception):
    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        details: list[Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details or []


def error_content(code: str, message: str, details: list[Any] | None = None) -> dict[str, object]:
    return {
        "error": {
            "code": code,
            "message": redact_sensitive_text(message),
            "details": redact_sensitive_data(details or []),
        }
    }


async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_content(exc.code, exc.message, exc.details),
    )


def _redact_validation_errors(errors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    redacted_errors = []
    for error in errors:
        redacted = dict(error)
        ctx = redacted.get("ctx")
        if isinstance(ctx, dict):
            redacted["ctx"] = {key: redact_sensitive_text(str(value)) for key, value in ctx.items()}
        loc = redacted.get("loc") or ()
        if any(is_sensitive_key(part) for part in loc):
            redacted["input"] = "[REDACTED]"
        else:
            redacted = redact_sensitive_data(redacted)
        redacted_errors.append(redacted)
    return redacted_errors


async def request_validation_error_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content=error_content(
            "validation_error",
            "Request validation failed.",
            _redact_validation_errors(exc.errors()),
        ),
    )


def raise_api_error(
    status_code: int,
    code: str,
    message: str,
    details: list[Any] | None = None,
) -> None:
    raise ApiError(status_code=status_code, code=code, message=message, details=details)
