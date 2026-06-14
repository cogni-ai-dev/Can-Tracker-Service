from collections.abc import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.database import get_sessionmaker


def get_app_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Generator[Session, None, None]:
    settings = get_app_settings(request)
    session_local = get_sessionmaker(settings.database_url)
    with session_local() as session:
        yield session
