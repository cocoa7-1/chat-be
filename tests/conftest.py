import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core import abuse
from app.api.v1 import chat
from app.core.database import Base, get_db
from app.core.logging import logger
from app.main import app


@pytest.fixture(autouse=True)
def fresh_request_guard(monkeypatch):
    """Each test gets its own budgets; production rate limits stay enabled."""
    monkeypatch.setattr(abuse, "guard", abuse.RequestGuard())


@pytest.fixture(autouse=True)
def capture_server_logs(caplog):
    logger.addHandler(caplog.handler)
    yield
    logger.removeHandler(caplog.handler)


@pytest.fixture
def isolated_chat(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite:///" + (tmp_path / "chat.db").as_posix(),
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)

    def db_dependency():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = db_dependency
    monkeypatch.setattr(chat, "SessionLocal", factory)
    try:
        with TestClient(app, raise_server_exceptions=False) as client:
            assert client.post("/api/v1/auth/register", json={
                "username": "reliability_user", "nickname": "Audit", "password": "auditPassword123"
            }).status_code == 201
            assert client.post("/api/v1/auth/login", json={
                "username": "reliability_user", "password": "auditPassword123"
            }).status_code == 200
            yield client, factory, engine
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
