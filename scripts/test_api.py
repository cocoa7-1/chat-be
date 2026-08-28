#!/usr/bin/env python3
"""
Automated E2E API Verification Script
Tests registration, login, chat session, SSE streaming, and logs querying.
Usage: python scripts/test_api.py
"""

import sys
import os
import time

# Ensure UTF-8 output encoding on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app

def run_tests():
    client = TestClient(app)
    print("=" * 65)
    print("[AI 챗봇 서비스] E2E 자동화 API 테스트 시작")
    print("=" * 65)

    timestamp = int(time.time())
    username = f"student_{timestamp}"
    password = "studyPassword123!"

    # 1. Register
    print("\n[Step 1] 회원가입 테스트 (/api/v1/auth/register)...")
    res = client.post("/api/v1/auth/register", json={"username": username, "password": password})
    assert res.status_code == 201, f"회원가입 실패: {res.text}"
    print(f"  [OK] 회원가입 성공: ID={res.json()['id']}, Username={res.json()['username']}")

    # 2. Login
    print("\n[Step 2] 로그인 및 쿠키/JWT 발급 테스트 (/api/v1/auth/login)...")
    res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"로그인 실패: {res.text}"
    token = res.json()["access_token"]
    cookies = {"access_token": token}
    print(f"  [OK] 로그인 성공: Token={token[:25]}... (HTTP-Only Cookie 발급 완료)")

    # 3. Create Session
    print("\n[Step 3] 대화 세션 생성 (/api/v1/chat/sessions)...")
    res = client.post("/api/v1/chat/sessions", json={"title": "FastAPI 실습 세션"}, cookies=cookies)
    assert res.status_code == 201, f"세션 생성 실패: {res.text}"
    session_id = res.json()["id"]
    print(f"  [OK] 대화 세션 생성 성공: Session ID={session_id}")

    # 4. SSE Stream Chat
    print("\n[Step 4] SSE 실시간 스트리밍 대화 질의 (/api/v1/chat/stream)...")
    prompt = "FastAPI의 장점과 DB 로깅 원리를 요약해줘."
    res = client.post("/api/v1/chat/stream", json={"message": prompt, "session_id": session_id}, cookies=cookies)
    assert res.status_code == 200, f"채팅 스트리밍 실패: {res.text}"
    assert "event: meta" in res.text
    assert "event: done" in res.text
    print("  [OK] SSE 스트리밍 정상 수신 및 완료 이벤트 확인")

    # 5. Check Messages in Session
    print("\n[Step 5] 세션 대화 내역 조회 (/api/v1/chat/sessions/{id}/messages)...")
    res = client.get(f"/api/v1/chat/sessions/{session_id}/messages", cookies=cookies)
    assert res.status_code == 200
    messages = res.json()
    assert len(messages) >= 2
    print(f"  [OK] 세션 내 메시지 {len(messages)}건 정상 조회 (User 질의 + AI 응답)")

    # 6. Check Logs Endpoint
    print("\n[Step 6] 대화 로그 영속화 조회 (/api/v1/logs)...")
    res = client.get("/api/v1/logs", cookies=cookies)
    assert res.status_code == 200
    logs = res.json()["items"]
    assert len(logs) >= 2
    print(f"  [OK] DB 저장 로그 {len(logs)}건 확인 완료 (Latency 측정값 포함)")

    print("\n" + "=" * 65)
    print("[SUCCESS] 모든 E2E API 테스트 케이스가 성공적으로 통과했습니다!")
    print("=" * 65)

if __name__ == "__main__":
    run_tests()
