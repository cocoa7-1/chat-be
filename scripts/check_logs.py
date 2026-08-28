#!/usr/bin/env python3
"""
CLI Tool for DB Verification & Audit
Evaluators and team members can run this script to inspect database records in real-time.
Usage: python scripts/check_logs.py
"""

import sys
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sqlalchemy import select, func, desc
from app.core.database import SessionLocal
from app.models.user import User
from app.models.chat import ChatSession, ChatMessage


def print_separator(title=""):
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)


def check_database_logs():
    db = SessionLocal()
    try:
        print_separator("[AI 챗봇 서비스] SQLite 데이터베이스 검증 리포트")

        # 1. User Summary
        users = db.scalars(select(User)).all()
        print(f"\n[1] 등록된 사용자 목록 (총 {len(users)}명):")
        print(f"    {'ID':<5} {'아이디':<15} {'가입일시':<22} {'활성상태':<8}")
        print("    " + "-" * 55)
        for u in users:
            print(f"    {u.id:<5} {u.username:<15} {u.created_at.strftime('%Y-%m-%d %H:%M:%S'):<22} {str(u.is_active):<8}")

        # 2. Chat Sessions Summary
        sessions = db.scalars(select(ChatSession)).all()
        print(f"\n[2] 대화 세션 목록 (총 {len(sessions)}개):")
        print(f"    {'ID':<5} {'유저ID':<8} {'세션 제목':<25} {'생성일시':<22}")
        print("    " + "-" * 65)
        for s in sessions:
            print(f"    {s.id:<5} {s.user_id:<8} {s.title[:22]:<25} {s.created_at.strftime('%Y-%m-%d %H:%M:%S'):<22}")

        # 3. Message Stats & Latency
        total_msgs = db.scalar(select(func.count(ChatMessage.id))) or 0
        ai_msgs = db.scalars(select(ChatMessage).where(ChatMessage.role == "assistant")).all()
        avg_latency = 0
        if ai_msgs:
            latencies = [m.latency_ms for m in ai_msgs if m.latency_ms]
            avg_latency = int(sum(latencies) / len(latencies)) if latencies else 0

        print(f"\n[3] 메시지 통계:")
        print(f"    - 총 메시지 수: {total_msgs}건 (사용자 질문 + AI 응답)")
        print(f"    - AI 응답 횟수: {len(ai_msgs)}회")
        print(f"    - 평균 지연 시간: {avg_latency} ms")

        # 4. Recent Detailed Conversation Logs
        print(f"\n[4] 최근 대화 로그 (최대 10건):")
        recent_logs = db.execute(
            select(ChatMessage, User.username)
            .join(User, ChatMessage.user_id == User.id)
            .order_by(desc(ChatMessage.created_at))
            .limit(10)
        ).all()

        if not recent_logs:
            print("    (기록된 대화 내역이 없습니다.)")
        else:
            print(f"    {'ID':<5} {'시간':<10} {'작성자':<10} {'구분':<10} {'지연':<8} {'상태':<8} {'내용 요약'}")
            print("    " + "-" * 75)
            for msg, username in recent_logs:
                time_str = msg.created_at.strftime("%H:%M:%S")
                lat_str = f"{msg.latency_ms}ms" if msg.latency_ms else "-"
                snippet = msg.content.replace("\n", " ")[:35] + ("..." if len(msg.content) > 35 else "")
                print(f"    {msg.id:<5} {time_str:<10} {username:<10} {msg.role:<10} {lat_str:<8} {msg.status:<8} {snippet}")

        print_separator("[OK] 데이터베이스 정상 검증 완료")

    except Exception as e:
        print(f"\n[ERROR] DB 조회 중 오류 발생: {e}")
    finally:
        db.close()


if __name__ == "__main__":
    check_database_logs()
