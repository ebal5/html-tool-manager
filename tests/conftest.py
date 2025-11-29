import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, StaticPool, create_engine

from html_tool_manager.core import db as core_db
from html_tool_manager.core.db import get_session
from html_tool_manager.main import app

# Use an in-memory SQLite database for testing with a static connection pool
# グローバルスコープの engine 定義は削除
# SQLALCHEMY_DATABASE_URL = "sqlite://"
# engine = create_engine(
#     SQLALCHEMY_DATABASE_URL,
#     connect_args={"check_same_thread": False},
#     poolclass=StaticPool,
# )


def override_get_session():
    """Yield a test session using the engine set by client_fixture."""
    with Session(core_db.engine) as session:
        yield session


app.dependency_overrides[get_session] = override_get_session


@pytest.fixture(name="session")
def session_fixture():
    """Create a new database engine and session for each test."""
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    # グローバルなエンジンをテスト用に差し替え
    original_core_engine = core_db.engine
    core_db.engine = engine

    # テーブル作成
    core_db.create_db_and_tables()

    with Session(engine) as session:
        yield session

    # テスト後にテーブルを破棄
    SQLModel.metadata.drop_all(engine)
    core_db.engine = original_core_engine


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create a test client that depends on the session fixture."""
    client = TestClient(app)
    yield client
