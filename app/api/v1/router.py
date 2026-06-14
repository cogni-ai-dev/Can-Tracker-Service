from fastapi import APIRouter, Depends

from app.api.deps import get_app_settings
from app.core.config import Settings

router = APIRouter()


@router.get("/meta", tags=["meta"])
def meta(settings: Settings = Depends(get_app_settings)) -> dict[str, object]:
    return {
        "service": "can-tracker-service",
        "api_version": "v1",
        "app_env": settings.app_env,
        "cors_enabled": bool(settings.cors_origin_list),
    }
