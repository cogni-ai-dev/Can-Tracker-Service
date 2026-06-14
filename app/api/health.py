import logging

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.api.deps import get_app_settings
from app.core.config import Settings
from app.core.database import check_database_ready

logger = logging.getLogger(__name__)
router = APIRouter(tags=["system"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready", response_model=None)
def ready(settings: Settings = Depends(get_app_settings)) -> dict[str, str] | JSONResponse:
    try:
        check_database_ready(settings.database_url)
    except Exception as exc:
        logger.warning("Readiness check failed: %s", exc)
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": {
                    "code": "service_unavailable",
                    "message": "Database connectivity check failed.",
                    "details": [],
                }
            },
        )
    return {"status": "ready"}
