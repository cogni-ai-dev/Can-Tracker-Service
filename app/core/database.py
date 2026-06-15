from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

DatabaseCacheKey = tuple[str, str | None]

_engines: dict[DatabaseCacheKey, Engine] = {}
_sessionmakers: dict[DatabaseCacheKey, sessionmaker[Session]] = {}


def _connect_args(database_url: str, database_schema: str | None = None) -> dict[str, object]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    if database_url.startswith("postgresql") and database_schema:
        return {"options": f"-csearch_path={database_schema},public"}
    return {}


def _database_config(
    database_url: str | None = None,
    database_schema: str | None = None,
) -> tuple[str, str | None]:
    settings = get_settings()
    url = database_url or settings.database_url
    if not url:
        raise RuntimeError("DATABASE_URL is required.")
    schema = database_schema if database_schema is not None else settings.database_schema
    return url, schema


def get_engine(database_url: str | None = None, database_schema: str | None = None) -> Engine:
    url, schema = _database_config(database_url, database_schema)
    key = (url, schema)
    if key not in _engines:
        _engines[key] = create_engine(
            url,
            connect_args=_connect_args(url, schema),
            future=True,
            pool_pre_ping=True,
        )
    return _engines[key]


def get_sessionmaker(database_url: str | None = None, database_schema: str | None = None) -> sessionmaker[Session]:
    url, schema = _database_config(database_url, database_schema)
    key = (url, schema)
    if key not in _sessionmakers:
        _sessionmakers[key] = sessionmaker(
            bind=get_engine(url, schema),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            future=True,
        )
    return _sessionmakers[key]


def get_session(
    database_url: str | None = None,
    database_schema: str | None = None,
) -> Generator[Session, None, None]:
    session_local = get_sessionmaker(database_url, database_schema)
    with session_local() as session:
        yield session


def check_database_ready(database_url: str | None = None, database_schema: str | None = None) -> None:
    with get_engine(database_url, database_schema).connect() as connection:
        connection.execute(text("SELECT 1"))


def clear_database_caches() -> None:
    for engine in _engines.values():
        engine.dispose()
    _engines.clear()
    _sessionmakers.clear()
