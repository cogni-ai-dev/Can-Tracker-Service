from collections.abc import Generator

import pytest
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import clear_database_caches, get_engine, get_sessionmaker
from app.models.base import Base


@pytest.fixture(autouse=True)
def isolated_settings_and_database_caches(monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()
    clear_database_caches()
    yield
    get_settings.cache_clear()
    clear_database_caches()


@pytest.fixture
def test_settings(tmp_path) -> Settings:
    return Settings(
        app_env="test",
        database_url=f"sqlite+pysqlite:///{tmp_path / 'test.db'}",
    )


@pytest.fixture
def db_engine(test_settings: Settings) -> Generator[Engine, None, None]:
    engine = get_engine(test_settings.database_url)
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def db_session(test_settings: Settings) -> Generator[Session, None, None]:
    session_local = get_sessionmaker(test_settings.database_url)
    with session_local() as session:
        yield session
