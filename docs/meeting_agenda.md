# 🤝 1차 킥오프 팀 미팅 회의록 및 아키텍처 합의록

> **미팅 일시**: 2026-08-28 (1차 미팅)  
> **참여자**: 4인 팀 전원 (감독, Auth 담당, Log/DB 담당, Chat/AI 담당)  
> **미팅 목적**: AI/SW 기초 텀프로젝트 미션 분석, 기술 스택 확정, 4인 역할 분담 및 협업 브랜치 전략 합의

---

## 📋 1. 확정된 시스템 아키텍처 및 기술 스택

1. **프론트엔드 & 백엔드 저장소 분리 (`cocoa7-1`)**
   - **프론트엔드 (`chat-fe`)**: HTML5 + TailwindCSS + Vanilla JS (ES6+) + SSE 실시간 스트리밍
     * **배포 방식**: [Vercel](https://vercel.com) 정적 호스팅 (무료 상시 외부 퍼블릭 HTTPS URL 제공)
   - **백엔드 (`chat-be`)**: Python, FastAPI, SQLite, SQLAlchemy 2.0 ORM, Google GenAI SDK
     * **배포 방식**: [AWS EC2 Free Tier](https://aws.amazon.com) 단일 인스턴스 데몬 배포
2. **도메인 컨셉 확정**
   - **컨셉**: 팀원의 건설 실무 배경을 살려 **"🏗️ 건설 안전 & 시공 전문 AI 튜터"**로 특화
   - **타겟 지식**: 산업안전보건법, 중대재해처벌법, 콘크리트/가설구조물 시공 지침, TBM 위험성 평가
3. **AI 모델 선정**
   - Google AI Studio **Gemma 4 26B (`gemma-4-26b-a4b-it`)** 채택 (빠른 TTFT, 넉넉한 무료 할당량, 30초 타임아웃 방어 및 스마트 Mock 모드)

---

## 👥 2. 4인 팀 역할 분담 및 브랜치 매핑

| 역할 (Role) | 브랜치 | 주요 담당 모듈 | 세부 업무 내용 |
| :--- | :--- | :--- | :--- |
| 👑 **감독 & 인프라 (Director)** | `main` / `develop` | 전체 아키텍처 검토, PR 리뷰, AWS EC2 배포 | 아키텍처 감독, PR 리뷰 및 머지, 브랜치 관리, AWS EC2 배포 및 인프라 운영 총괄 |
| 🛡️ **Role 1: 인증 & 보안 (Auth)** | `dev/auth` | `app/api/v1/auth.py`<br>`app/core/security.py`<br>`app/models/user.py` | 회원가입, 로그인, Bcrypt 비밀번호 암호화, JWT 검증 의존성(`deps.py`), 건설 도메인 연계 |
| 💾 **Role 2: 데이터 & 로깅 (Log/DB)** <br>*(질문자 본인)* | `dev/log` | `app/api/v1/logs.py`<br>`app/core/database.py`<br>`app/models/chat.py`<br>`scripts/check_logs.*` | SQLite 세션/메시지 ORM 모델링, Request ID 미들웨어, 4대 표준 로깅, DB 로그 검증 도구 |
| 🤖 **Role 3: AI 파이프라인 (Chat)** | `dev/chat` | `app/services/gemini_service.py`<br>`app/api/v1/chat.py`<br>`app/schemas/chat.py` | Gemma 4 26B API 연동, SSE 실시간 스트리밍, 대화 문맥(최근 10개) 조립, 타임아웃 방어 |
| 🌐 **프론트엔드 (Frontend)** | `dev/frontend` | `chat-fe/index.html`<br>`chat-fe/login.html`<br>`chat-fe/logs.html`<br>`chat-fe/js/` | 반응형 채팅 UI, SSE 스트림 수신 렌더링, 대화 로그 확인 화면, Vercel 배포 |

---

## 🔄 3. 작업 및 Git 협업 규칙

1. **탑다운(Top-Down) 학습 및 개발**: 완성된 뼈대 코드를 기반으로 각자 브랜치에서 기능 수정 및 분석 진행.
2. **로컬 독립 실행**: AWS나 API 키 없이도 누구나 로컬에서 가상환경 하나로 100% 실행 및 테스트 가능.
3. **커밋 기준**: 미션 평가 기준 충족을 위해 각자 파트에서 10회 이상 유의미한 커밋을 나누어 작성 (`docs/roles/` 가이드 참조).
4. **PR 및 머지**: 자기 브랜치(`dev/auth`, `dev/log`, `dev/chat`)에서 작업 완료 후 `develop` 브랜치로 PR 생성 및 감독 리뷰 후 머지.
