import logging
import re
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import REQUEST_ID_CONTEXT

REQUEST_ID_HEADER = "x-request-id"
REQUEST_ID_RESPONSE_HEADER = "X-Request-ID"
REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")

logger = logging.getLogger("app.request")


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = safe_request_id(request.headers.get(REQUEST_ID_HEADER))
        request.state.request_id = request_id
        token = REQUEST_ID_CONTEXT.set(request_id)
        started_at = time.perf_counter()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers[REQUEST_ID_RESPONSE_HEADER] = request_id
            return response
        except Exception:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.exception(
                "request_failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "client": request.client.host if request.client else None,
                },
            )
            raise
        finally:
            duration_ms = round((time.perf_counter() - started_at) * 1000, 2)
            logger.info(
                "request_completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": status_code,
                    "duration_ms": duration_ms,
                    "client": request.client.host if request.client else None,
                },
            )
            REQUEST_ID_CONTEXT.reset(token)


def safe_request_id(value: str | None) -> str:
    if value and REQUEST_ID_PATTERN.fullmatch(value):
        return value
    return uuid4().hex
