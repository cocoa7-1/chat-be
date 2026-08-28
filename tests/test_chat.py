import pytest
import time
from fastapi.testclient import TestClient
from app.main import app


def test_chat_pipeline():
    client = TestClient(app)
    # 1. Register & Login test user
    username = f"chatuser_{int(time.time())}"
    password = "chatPassword123"

    client.post("/api/v1/auth/register", json={"username": username, "password": password})
    login_res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert login_res.status_code == 200

    # 2. Create Session
    session_res = client.post("/api/v1/chat/sessions", json={"title": "FastAPI 질문 세션"})
    assert session_res.status_code == 201
    session_id = session_res.json()["id"]

    # 3. Stream Chat Request
    stream_res = client.post(
        "/api/v1/chat/stream",
        json={"message": "FastAPI의 장점은 무엇인가요?", "session_id": session_id}
    )
    assert stream_res.status_code == 200
    assert "text/event-stream" in stream_res.headers["content-type"]
    assert "event: meta" in stream_res.text
    assert "event: done" in stream_res.text

    # 4. Check Messages in Session
    msg_res = client.get(f"/api/v1/chat/sessions/{session_id}/messages")
    assert msg_res.status_code == 200
    messages = msg_res.json()
    assert len(messages) >= 2  # user + assistant

    # 5. Check Logs Endpoint
    logs_res = client.get("/api/v1/logs")
    assert logs_res.status_code == 200
    logs = logs_res.json()["items"]
    assert len(logs) >= 2
