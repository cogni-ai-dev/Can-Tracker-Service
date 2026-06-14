from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings

_engines: dict[str, Engine] = {}
_sessionmakers: dict[str, sessionmaker[Session]] = {}


def _connect_args(database_url: str) -> dict[str, object]:
    if database_url.startswith("sqlite"):
        return {"check_same_thread": False}
    return {}


def get_engine(database_url: str | None = None) -> Engine:
    url = database_url or get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is required.")
    if url not in _engines:
        _engines[url] = create_engine(
            url,
            connect_args=_connect_args(url),
            future=True,
            pool_pre_ping=True,
        )
    return _engines[url]


def get_sessionmaker(database_url: str | None = None) -> sessionmaker[Session]:
    url = database_url or get_settings().database_url
    if not url:
        raise RuntimeError("DATABASE_URL is required.")
    if url not in _sessionmakers:
        _sessionmakers[url] = sessionmaker(
            bind=get_engine(url),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
            future=True,
        )
    return _sessionmakers[url]


def get_session(database_url: str | None = None) -> Generator[Session, None, None]:
    session_local = get_sessionmaker(database_url)
    with session_local() as session:
        yield session


def check_database_ready(database_url: str | None = None) -> None:
    with get_engine(database_url).connect() as connection:
        connection.execute(text("SELECT 1"))


def clear_database_caches() -> None:
    for engine in _engines.values():
        engine.dispose()
    _engines.clear()
    _sessionmakers.clear()
