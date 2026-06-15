from sqlalchemy import Column, Integer, Table, inspect, text

from app.core.database import _connect_args
from app.models.base import Base


def test_session_can_execute_basic_statement(db_session) -> None:
    assert db_session.execute(text("SELECT 1")).scalar_one() == 1


def test_postgresql_database_schema_sets_search_path() -> None:
    assert _connect_args("postgresql+psycopg://user:pass@localhost:5432/can", "can_tracker") == {
        "options": "-csearch_path=can_tracker,public",
    }


def test_test_database_schema_can_be_created_and_torn_down(db_engine) -> None:
    smoke_table = Table(
        "test_schema_smoke",
        Base.metadata,
        Column("id", Integer, primary_key=True),
        extend_existing=True,
    )

    try:
        smoke_table.create(db_engine)
        assert "test_schema_smoke" in inspect(db_engine).get_table_names()
    finally:
        smoke_table.drop(db_engine, checkfirst=True)
        Base.metadata.remove(smoke_table)

    assert "test_schema_smoke" not in inspect(db_engine).get_table_names()
