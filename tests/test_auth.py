import pytest
import time
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, engine


@pytest.fixture(autouse=True)
def setup_database():
    Base.metadata.create_all(bind=engine)
    yield


def test_register_and_login():
    client = TestClient(app)
    username = f"testuser_{int(time.time())}"
    password = "securePassword123"

    # 1. Register
    reg_res = client.post("/api/v1/auth/register", json={
        "username": username,
        "password": password
    })
    assert reg_res.status_code == 201
    assert reg_res.json()["username"] == username

    # 2. Duplicate Register should fail
    dup_res = client.post("/api/v1/auth/register", json={
        "username": username,
        "password": password
    })
    assert dup_res.status_code == 400

    # 3. Login
    login_res = client.post("/api/v1/auth/login", json={
        "username": username,
        "password": password
    })
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert data["user"]["username"] == username

    # 4. Check me endpoint
    me_res = client.get("/api/v1/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["username"] == username


def test_unauthorized_access():
    fresh_client = TestClient(app)
    res = fresh_client.get("/api/v1/chat/sessions")
    assert res.status_code == 401
