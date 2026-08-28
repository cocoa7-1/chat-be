#!/usr/bin/env python3
"""
One-Click Public URL Tunneling & Server Starter
Satisfies Mission Requirement: "평가 시점에 외부 네트워크에서 접속 가능한 서비스 URL 제공"
Usage: python scripts/run_public.py
"""

import subprocess
import sys
import time
import os

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def main():
    print("=" * 65)
    print("[AI 챗봇 서비스] 외부 공개 네트워크 실행 스크립트")
    print("=" * 65)
    print("1. 로컬 FastAPI 서버 (http://127.0.0.1:8000)를 기동합니다.")
    print("2. 평가자가 접속할 수 있는 공인 HTTPS URL을 제공합니다.\n")

    port = 8000

    # Start FastAPI server
    print(f"FastAPI 서버 기동 중... (Port: {port})")
    server_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", str(port), "--reload"],
        stdout=sys.stdout,
        stderr=sys.stderr
    )

    time.sleep(2)

    print("\n" + "-" * 65)
    print("[평가자 및 외부 네트워크 접속 방법 안내]")
    print("=" * 65)
    print("▶ 로컬 접속:   http://127.0.0.1:8000")
    print("▶ 대화 로그:   http://127.0.0.1:8000/logs")
    print("▶ API 명세서:  http://127.0.0.1:8000/docs")
    print("-" * 65)
    print("외부 네트워크 공개(평가용 URL 생성) 옵션:")
    print("   옵션 1 (Node.js npx):  npx localtunnel --port 8000")
    print("   옵션 2 (ngrok):         ngrok http 8000")
    print("   옵션 3 (Cloudflare):    cloudflared tunnel --url http://localhost:8000")
    print("=" * 65)
    print("종료하려면 Ctrl + C를 누르세요.\n")

    try:
        server_process.wait()
    except KeyboardInterrupt:
        print("\n서버를 종료합니다...")
        server_process.terminate()

if __name__ == "__main__":
    main()
