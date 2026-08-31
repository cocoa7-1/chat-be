import pytest
import time
from sqlalchemy import select
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import SessionLocal, init_db
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage
from app.core.security import get_password_hash


def test_database_models_and_relationships():
    init_db()
    db = SessionLocal()
    try:
        # Create user
        username = f"dbuser_{int(time.time())}"
        user = User(username=username, password_hash=get_password_hash("pass123"))
        db.add(user)
        db.commit()
        db.refresh(user)
        assert user.id is not None

        # Create session
        session = ChatSession(user_id=user.id, title="DB 테스트 대화방")
        db.add(session)
        db.commit()
        db.refresh(session)
        assert session.id is not None

        # Create user message & assistant message
        msg1 = ChatMessage(session_id=session.id, user_id=user.id, role="user", content="테스트 질문")
        msg2 = ChatMessage(session_id=session.id, user_id=user.id, role="assistant", content="테스트 답변", latency_ms=120)
        db.add_all([msg1, msg2])
        db.commit()

        # Check relationships
        retrieved_session = db.scalar(select(ChatSession).where(ChatSession.id == session.id))
        assert len(retrieved_session.messages) == 2
        assert retrieved_session.user.username == username

        # Cascade delete test
        db.delete(user)
        db.commit()

        deleted_session = db.scalar(select(ChatSession).where(ChatSession.id == session.id))
        assert deleted_session is None
    finally:
        db.close()


def test_log_pagination_and_session_filtering():
    client = TestClient(app)
    username = f"loguser_{int(time.time())}"
    password = "LogPassword123"

    # Register & login
    client.post("/api/v1/auth/register", json={"username": username, "password": password})
    login_res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert login_res.status_code == 200

    # Create 2 sessions
    s1 = client.post("/api/v1/chat/sessions", json={"title": "세션 A"}).json()["id"]
    s2 = client.post("/api/v1/chat/sessions", json={"title": "세션 B"}).json()["id"]

    # Send messages to session A
    client.post("/api/v1/chat/stream", json={"message": "질문 A-1", "session_id": s1})
    client.post("/api/v1/chat/stream", json={"message": "질문 A-2", "session_id": s1})

    # Send message to session B
    client.post("/api/v1/chat/stream", json={"message": "질문 B-1", "session_id": s2})

    # Test session A filter
    res_s1 = client.get(f"/api/v1/logs?session_id={s1}")
    assert res_s1.status_code == 200
    data_s1 = res_s1.json()
    assert data_s1["total"] == 4  # 2 questions + 2 answers
    for item in data_s1["items"]:
        assert item["session_id"] == s1

    # Test session B filter
    res_s2 = client.get(f"/api/v1/logs?session_id={s2}")
    assert res_s2.status_code == 200
    data_s2 = res_s2.json()
    assert data_s2["total"] == 2  # 1 question + 1 answer

    # Test pagination (limit=2, offset=0)
    page_res = client.get(f"/api/v1/logs?limit=2&offset=0")
    assert page_res.status_code == 200
    page_data = page_res.json()
    assert page_data["total"] >= 6
    assert len(page_data["items"]) == 2


def test_log_statistics_endpoint():
    client = TestClient(app)
    username = f"statsuser_{int(time.time())}"
    password = "StatsPassword123"

    # Register & login
    client.post("/api/v1/auth/register", json={"username": username, "password": password})
    client.post("/api/v1/auth/login", json={"username": username, "password": password})

    # Create session and stream chat
    sess_id = client.post("/api/v1/chat/sessions", json={"title": "통계 검증 세션"}).json()["id"]
    client.post("/api/v1/chat/stream", json={"message": "건설 안전 질문입니다.", "session_id": sess_id})

    # Query stats endpoint
    stats_res = client.get("/api/v1/logs/stats")
    assert stats_res.status_code == 200
    stats = stats_res.json()

    assert stats["total_messages"] >= 2
    assert stats["total_questions"] >= 1
    assert stats["total_answers"] >= 1
    assert stats["total_sessions"] >= 1
    assert stats["avg_latency_ms"] >= 0
    assert stats["success_rate_percent"] == 100.0

