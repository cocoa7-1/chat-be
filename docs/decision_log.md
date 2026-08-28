# 🏗️ 건설 안전 & 시공 AI 튜터 서비스 - 아키텍처 결정 기록 및 학습 가이드 (ADR)

> **문서 목적**: 본 문서는 팀 프로젝트의 핵심 아키텍처 의사결정(Architecture Decision Records, ADR)과 그 근거를 기록하여, 팀원들과의 역할 분담, 브랜치 협업 및 배포 시 참고할 수 있도록 작성되었습니다.

---

## 1. 프로젝트 개요 및 미션 분석

- **프로젝트명**: 건설 안전 & 시공 전문 AI 튜터 챗봇 서비스 (`chat-be` & `chat-fe`)
- **타겟 도메인**: 산업안전보건법, 중대재해처벌법, 콘크리트/골조 시공 지침, TBM(Tool Box Meeting) 및 위험성 평가
- **핵심 기술 스택**:
  - **백엔드**: Python, FastAPI, SQLite, SQLAlchemy 2.0 ORM, Google GenAI (Gemma 4 26B)
  - **프론트엔드**: HTML5, TailwindCSS (CDN), Vanilla JS (ES6+), SSE 실시간 스트리밍
  - **배포 환경**: 프론트엔드(Vercel 정적 배포) + 백엔드(AWS EC2 Free Tier)

---

## 2. 핵심 아키텍처 결정 내역 (Decision Records)

### [ADR-01] 프론트엔드/백엔드 저장소 분리 및 Vercel + AWS EC2 배포
- **결정**: **독립된 2개 저장소(`chat-fe`, `chat-be`) 분리 운영 및 Vercel(FE) + AWS EC2(BE) 배포**
- **선택 이유**:
  - `chat-fe`는 빌드 없는 순수 HTML/JS 정적 사이트로 Vercel을 통해 **무료 상시 외부 접속 HTTPS URL**을 즉시 확보.
  - `chat-be`는 AWS EC2 프리티어 인스턴스 1대에서 단일 데몬으로 경량 SQLite와 함께 배포하여 인프라 비용 0원 유지.
  - CORS 미들웨어를 통해 Vercel 도메인과 EC2 백엔드 간 안전한 REST/SSE 통신 지원.

### [ADR-02] AI 모델: Google AI Studio Gemma 4 26B 채택
- **결정**: **Google AI Studio의 Gemma 4 26B(`gemma-4-26b-a4b-it`) 기본 모델 채택 + 최근 10개 롤링 윈도우 컨텍스트**
- **선택 이유**:
  - 26B 모델은 빠른 토큰 생성 속도(TTFT)와 넉넉한 무료 할당량을 제공하여 실시간 챗봇에 가장 이상적임.
  - 최근 10개 대화 이력을 프롬프트에 주입하여 "아까 질문한 거 이어서 설명해줘" 같은 연속적 대화 문맥 유지.
  - 30초 타임아웃 방어 및 API 키 미설정 시 자동 동작하는 스마트 Mock 모드 구현.

### [ADR-03] 데이터베이스: SQLite + SQLAlchemy 2.0 ORM
- **결정**: **SQLite 파일 DB + SQLAlchemy 2.0 (Select/Session) + 검증 도구 3종 제공**
- **선택 이유**:
  - 별도 DB 서버 설치 없이 단일 파일(`chatbot.db`)로 동작하여 팀원들의 로컬 학습 및 평가자 검증에 최적.
  - `scripts/check_logs.py`, `scripts/check_logs.sql`, `logs.html`을 통해 실시간 DB 적재 상태를 다각도로 검증 가능.

### [ADR-04] 사용자 인증: 단방향 Bcrypt 해시 + JWT 토큰
- **결정**: **Passlib(Bcrypt) 비밀번호 암호화 + JWT 액세스 토큰 (`Authorization: Bearer` 헤더)**
- **선택 이유**:
  - 평문 비밀번호 저장 금지 보안 원칙 준수.
  - Vercel(FE)과 EC2(BE) 간의 Cross-Origin 통신에서 브라우저 서드파티 쿠키 차단 문제를 방지하기 위해 Bearer 토큰 헤더 방식을 기본 지원.

### [ADR-05] 로깅 및 운영 모니터링: 4대 표준 이벤트
- **결정**: **Request ID 미들웨어 + 4대 필수 이벤트 포맷팅**
- **선택 이유**:
  - 미션 평가 기준인 `request_received`, `ai_call_start`, `ai_call_success`, `db_save_success`를 구조화된 로그로 출력하여 요청 전체 수명주기 추적.

### [ADR-06] 실시간 토큰 스트리밍 (SSE)
- **결정**: **Server-Sent Events (SSE, `text/event-stream`) 기반 토큰 단위 실시간 전송**
- **선택 이유**:
  - 답변이 모두 생성될 때까지 대기하지 않고, 타이핑 효과를 즉시 제공하여 체감 응답 속도 극대화.
  - 스트리밍 완료 시점에 총 지연시간(`latency_ms`)을 계산하여 DB에 비동기 저장.

---

## 3. 데이터베이스 ERD 구조

```text
+------------------+       +---------------------+       +-----------------------+
|      users       |       |    chat_sessions    |       |     chat_messages     |
+------------------+       +---------------------+       +-----------------------+
| id (PK, Integer) |1     N| id (PK, Integer)    |1     N| id (PK, Integer)      |
| username (Str)   |<----->| user_id (FK, Users) |<----->| session_id (FK, Sess) |
| password_hash    |       | title (Str)         |       | user_id (FK, Users)   |
| is_active (Bool) |       | created_at          |       | role (user/assistant) |
| is_admin (Bool)  |       | updated_at          |       | content (Text)        |
| created_at       |       +---------------------+       | latency_ms (Integer)  |
+------------------+                                     | status (success/err)  |
                                                         | error_message (Text)  |
                                                         | created_at            |
                                                         +-----------------------+
```

---

## 4. 4인 팀 역할 분담 및 브랜치 매핑

| 역할 (Role) | 브랜치 | 주요 담당 컴포넌트 | 세부 업무 내용 |
| :--- | :--- | :--- | :--- |
| 👑 **감독 & 인프라 (Director)** | `main` / `develop` | 전체 아키텍처 검토, PR 리뷰, AWS EC2 배포 | 코드 리뷰 및 머지, 브랜치 관리, AWS EC2 배포 및 인프라 운영 총괄 |
| 🛡️ **Role 1: 인증 & 보안 (Auth)** | `dev/auth` | `app/api/v1/auth.py`<br>`app/core/security.py`<br>`app/models/user.py` | 회원가입, 로그인, Bcrypt 패스워드 암호화, JWT 검증 의존성(`deps.py`), 건설 도메인 연계 |
| 💾 **Role 2: 데이터 & 로깅 (DB/Log)** <br>*(질문자 본인)* | `dev/log` | `app/api/v1/logs.py`<br>`app/core/database.py`<br>`app/models/chat.py`<br>`scripts/check_logs.*` | SQLite 세션/메시지 ORM 모델링, Request ID 미들웨어, 4대 표준 로깅, DB 로그 검증 도구 |
| 🤖 **Role 3: AI 파이프라인 (Chat)** | `dev/chat` | `app/services/gemini_service.py`<br>`app/api/v1/chat.py`<br>`app/schemas/chat.py` | Gemma 4 26B API 연동, SSE 스트리밍, 대화 문맥 조립, 30초 타임아웃 방어 및 Mock 모드 |
| 🌐 **프론트엔드 (Frontend)** | `dev/frontend` | `chat-fe/index.html`<br>`chat-fe/login.html`<br>`chat-fe/logs.html`<br>`chat-fe/js/` | 반응형 채팅 UI, SSE 스트림 수신 렌더링, 대화 로그 확인 화면, Vercel 배포 |
