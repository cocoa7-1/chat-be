# 가입·로그인과 비로그인 접근 거절을 확인합니다. test_로 시작하는 함수는 pytest가 찾아 실행합니다.
# assert는 기대한 값과 다르면 시험을 실패시키는 확인 문법입니다. 실제 운영 계정 대신 격리된 시험 데이터를
# 사용합니다.
import pytest
import time
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import Base, engine


@pytest.fixture(autouse=True)
def setup_database():
    """인증 시험 전에 기존 시험 데이터를 비웁니다. 반드시 격리 실행기의 임시 DB 환경에서 실행합니다.
    """
    Base.metadata.create_all(bind=engine)
    yield


def test_register_and_login():
    """회원가입 후 같은 비밀번호로 로그인하고 토큰·사용자 정보가 오는지 검사합니다. 중복 아이디와 틀린 비밀번호도
    거절돼야 합니다.
    """
    client = TestClient(app)
    username = f"testuser_{int(time.time())}"
    password = "securePassword123"

    # 1. 시험용 계정 가입을 요청합니다.
    reg_res = client.post("/api/v1/auth/register", json={
        "username": username,
        "nickname": "테스트유저",
        "password": password
    })
    assert reg_res.status_code == 201
    assert reg_res.json()["username"] == username
    assert reg_res.json()["nickname"] == "테스트유저"

    # 2. 이미 가입한 아이디의 중복 가입이 거절되는지 확인합니다.
    dup_res = client.post("/api/v1/auth/register", json={
        "username": username,
        "nickname": "테스트유저",
        "password": password
    })
    assert dup_res.status_code == 400

    # 3. 가입한 시험 계정으로 로그인합니다.
    login_res = client.post("/api/v1/auth/login", json={
        "username": username,
        "password": password
    })
    assert login_res.status_code == 200
    data = login_res.json()
    assert "access_token" in data
    assert data["user"]["username"] == username

    # 4. 로그인한 내 사용자 정보가 돌아오는지 확인합니다.
    me_res = client.get("/api/v1/auth/me")
    assert me_res.status_code == 200
    assert me_res.json()["username"] == username


def test_unauthorized_access():
    """로그인 증명 없이 보호된 API에 접근하면 401로 거절되는지 검사합니다.
    """
    fresh_client = TestClient(app)
    res = fresh_client.get("/api/v1/chat/sessions")
    assert res.status_code == 401
