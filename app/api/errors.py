from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


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
            "message": message,
            "details": details or [],
        }
    }


async def api_error_handler(_request: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=error_content(exc.code, exc.message, exc.details),
    )


def raise_api_error(
    status_code: int,
    code: str,
    message: str,
    details: list[Any] | None = None,
) -> None:
    raise ApiError(status_code=status_code, code=code, message=message, details=details)
