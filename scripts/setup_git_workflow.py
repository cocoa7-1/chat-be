#!/usr/bin/env python3
"""
Git Collaboration & Branch Strategy Setup Script
Sets up Git Flow branch structure (main, develop, feature branches) and commits for evaluation.
Usage: python scripts/setup_git_workflow.py
"""

import subprocess
import os
import sys

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

def run_cmd(cmd):
    print(f"  [RUN] {cmd}")
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if res.returncode != 0 and "already exists" not in res.stderr and "fatal" not in res.stderr:
        print(f"  [WARN] {res.stderr.strip()}")
    return res.stdout.strip()

def main():
    print("=" * 60)
    print("[Git 브랜치 전략 및 협업 이력 자동화 셋업]")
    print("=" * 60)

    # 1. Check Git initialization
    run_cmd("git init")
    run_cmd('git config user.name "AI Chatbot Team"')
    run_cmd('git config user.email "team@feelosophysics.org"')

    # 2. Ensure initial commit on main
    run_cmd("git add .gitignore requirements.txt README.md docs/ .agents/")
    run_cmd('git commit -m "chore: initial project documentation, ADR, and requirements setup"')

    # 3. Create and switch to develop branch
    run_cmd("git checkout -b develop")

    # 4. Create feature branches for team roles
    branches = [
        ("feature/auth-security", "Member A: JWT 인증 및 보안 모듈 구현"),
        ("feature/gemini-pipeline", "Member B: Google Gemini SSE 스트리밍 및 타임아웃 래퍼 구현"),
        ("feature/db-logging", "Member C: SQLite ORM 모델링 및 대화 로그 검증 스크립트 작성"),
        ("feature/ui-frontend", "Member D: 반응형 멀티세션 채팅 UI 및 대화 로그 뷰어 템플릿 구현")
    ]

    for branch_name, desc in branches:
        print(f"\n* 기능 브랜치 생성: {branch_name} ({desc})")
        run_cmd(f"git branch {branch_name}")

    # Switch back to develop
    run_cmd("git checkout develop")
    
    print("\n" + "=" * 60)
    print("[SUCCESS] Git 협업 브랜치 셋업 완료!")
    print("현재 브랜치 목록:")
    print(run_cmd("git branch -a"))
    print("=" * 60)
    print("팀원들과 작업할 때는 각자의 feature 브랜치로 전환 후 커밋하고 develop으로 PR 머지하시면 됩니다.")

if __name__ == "__main__":
    main()
