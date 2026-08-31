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


# ANSI Color Codes
RESET = "\033[0m"
BOLD = "\033[1m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
GRAY = "\033[90m"
MAGENTA = "\033[95m"


def format_latency(latency_ms):
    """Format latency with ANSI color badges based on performance thresholds."""
    if latency_ms is None or latency_ms == 0:
        return f"{GRAY}-         {RESET}"
    if latency_ms < 3000:
        return f"{GREEN}⚡ {latency_ms:<5}ms{RESET}"
    elif latency_ms < 7000:
        return f"{YELLOW}⏳ {latency_ms:<5}ms{RESET}"
    else:
        return f"{RED}⚠️ {latency_ms:<5}ms{RESET}"


def format_role(role):
    """Format role with construction domain emojis."""
    if role == "user":
        return f"{CYAN}👷 user     {RESET}"
    elif role == "assistant":
        return f"{MAGENTA}🤖 assistant{RESET}"
    return f"{role:<12}"


def format_status(status):
    """Format execution status with visual icons."""
    if status == "success":
        return f"{GREEN}✅ OK {RESET}"
    elif status == "error":
        return f"{RED}❌ ERR{RESET}"
    return f"{status:<6}"


def print_separator(title=""):
    print("\n" + "=" * 78)
    if title:
        print(f"  {BOLD}{title}{RESET}")
        print("=" * 78)


def check_database_logs():
    db = SessionLocal()
    try:
        print_separator("🏗️ [AI 챗봇 서비스] SQLite 데이터베이스 검증 리포트 (Log/DB Audit)")

        # 1. User Summary
        users = db.scalars(select(User)).all()
        print(f"\n👥 {BOLD}[1] 등록된 사용자 목록 (총 {len(users)}명):{RESET}")
        print(f"    {'ID':<5} {'아이디':<22} {'가입일시':<22} {'활성상태':<8}")
        print("    " + "-" * 62)
        for u in users:
            status_badge = f"{GREEN}True{RESET}" if u.is_active else f"{RED}False{RESET}"
            print(f"    {u.id:<5} {u.username:<22} {u.created_at.strftime('%Y-%m-%d %H:%M:%S'):<22} {status_badge}")

        # 2. Chat Sessions Summary
        sessions = db.scalars(select(ChatSession)).all()
        print(f"\n💬 {BOLD}[2] 대화 세션 목록 (총 {len(sessions)}개):{RESET}")
        print(f"    {'ID':<5} {'유저ID':<8} {'세션 제목':<28} {'생성일시':<22}")
        print("    " + "-" * 68)
        for s in sessions:
            print(f"    {s.id:<5} {s.user_id:<8} {s.title[:25]:<28} {s.created_at.strftime('%Y-%m-%d %H:%M:%S'):<22}")

        # 3. Message Stats & Latency KPI
        total_msgs = db.scalar(select(func.count(ChatMessage.id))) or 0
        ai_msgs = db.scalars(select(ChatMessage).where(ChatMessage.role == "assistant")).all()
        user_msgs = db.scalars(select(ChatMessage).where(ChatMessage.role == "user")).all()
        avg_latency = 0
        latencies = [m.latency_ms for m in ai_msgs if m.latency_ms]
        if latencies:
            avg_latency = int(sum(latencies) / len(latencies))

        latency_badge = format_latency(avg_latency) if avg_latency else f"{GRAY}0ms{RESET}"

        print(f"\n📊 {BOLD}[3] 메시지 통계 & 성능 메트릭 (KPIs):{RESET}")
        print(f"    - 총 메시지 수: {BOLD}{total_msgs}{RESET}건 (👷 질문 {len(user_msgs)}건 + 🤖 AI 답변 {len(ai_msgs)}건)")
        print(f"    - AI 응답률: {GREEN}{int((len(ai_msgs) / len(user_msgs) * 100)) if user_msgs else 0}%{RESET}")
        print(f"    - 평균 AI 응답 지연: {latency_badge} (기준: ⚡ <3s, ⏳ <7s, ⚠️ >=7s)")

        # 4. Recent Detailed Conversation Logs
        print(f"\n📜 {BOLD}[4] 최근 대화 로그 (최대 10건):{RESET}")
        recent_logs = db.execute(
            select(ChatMessage, User.username)
            .join(User, ChatMessage.user_id == User.id)
            .order_by(desc(ChatMessage.created_at))
            .limit(10)
        ).all()

        if not recent_logs:
            print("    (기록된 대화 내역이 없습니다.)")
        else:
            print(f"    {'ID':<5} {'시간':<10} {'작성자':<20} {'구분':<12} {'지연시간':<11} {'상태':<8} {'내용 요약'}")
            print("    " + "-" * 88)
            for msg, username in recent_logs:
                time_str = msg.created_at.strftime("%H:%M:%S")
                lat_str = format_latency(msg.latency_ms)
                role_str = format_role(msg.role)
                status_str = format_status(msg.status)
                snippet = msg.content.replace("\n", " ")[:32] + ("..." if len(msg.content) > 32 else "")
                print(f"    {msg.id:<5} {time_str:<10} {username:<20} {role_str} {lat_str}  {status_str} {snippet}")

        print_separator(f"{GREEN}✅ [OK] SQLite 데이터베이스 및 로깅 감사 정상 완료{RESET}")

    except Exception as e:
        print(f"\n{RED}[ERROR] DB 조회 중 오류 발생: {e}{RESET}")
    finally:
        db.close()


if __name__ == "__main__":
    check_database_logs()

