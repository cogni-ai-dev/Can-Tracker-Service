import httpx
import pytest

from app.core.config import Settings
from app.main import create_app


@pytest.mark.asyncio
async def test_health_does_not_require_database(tmp_path) -> None:
    settings = Settings(
        app_env="test",
        database_url=f"sqlite+pysqlite:///{tmp_path / 'missing' / 'health.db'}",
    )
    transport = httpx.ASGITransport(app=create_app(settings=settings))

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_ready_returns_ok_when_database_connects(tmp_path) -> None:
    settings = Settings(
        app_env="test",
        database_url=f"sqlite+pysqlite:///{tmp_path / 'ready.db'}",
    )
    transport = httpx.ASGITransport(app=create_app(settings=settings))

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


@pytest.mark.asyncio
async def test_ready_returns_controlled_failure_when_database_is_unavailable(tmp_path) -> None:
    settings = Settings(
        app_env="test",
        database_url=f"sqlite+pysqlite:///{tmp_path / 'missing' / 'ready.db'}",
    )
    transport = httpx.ASGITransport(app=create_app(settings=settings))

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "service_unavailable",
            "message": "Database connectivity check failed.",
            "details": [],
        }
    }


@pytest.mark.asyncio
async def test_meta_returns_environment_safe_metadata(tmp_path) -> None:
    settings = Settings(
        app_env="test",
        database_url=f"sqlite+pysqlite:///{tmp_path / 'meta.db'}",
        cors_origins="http://localhost:8000",
    )
    transport = httpx.ASGITransport(app=create_app(settings=settings))

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/api/v1/meta")

    assert response.status_code == 200
    assert response.json() == {
        "service": "can-tracker-service",
        "api_version": "v1",
        "app_env": "test",
        "cors_enabled": True,
    }
