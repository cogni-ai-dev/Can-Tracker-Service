from fastapi import APIRouter, Depends

from app.api.deps import get_app_settings
from app.api.v1.auth import router as auth_router
from app.api.v1.users import router as users_router
from app.core.config import Settings

router = APIRouter()
router.include_router(auth_router)
router.include_router(users_router)


@router.get("/meta", tags=["meta"])
def meta(settings: Settings = Depends(get_app_settings)) -> dict[str, object]:
    return {
        "service": "can-tracker-service",
        "api_version": "v1",
        "app_env": settings.app_env,
        "cors_enabled": bool(settings.cors_origin_list),
    }
