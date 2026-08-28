# 웹 기반 AI 챗봇 서비스 개발 - 아키텍처 결정 기록 및 학습 가이드 (ADR)

> **문서 목적**: 본 문서는 팀 프로젝트 사전 준비 과정에서 이루어진 기술적 의사결정(Architecture Decision Records, ADR)과 그 근거를 기록하여, 팀원들과의 역할 분담 및 구현 학습 시 참고할 수 있도록 작성되었습니다.

---

## 1. 프로젝트 개요 및 미션 분석

- **프로젝트명**: 웹 기반 AI 챗봇 서비스 개발 프로젝트 (FastAPI)
- **학습 목표**: Linux, FastAPI Web, SQLite Database, AI API(Gemini)를 하나의 유기적 파이프라인으로 통합 구축하고, 실무 수준의 운영 안정성(로깅, 타임아웃, 예외 처리, 인증/보안)을 확보함.
- **핵심 요구사항 요약**:
  1. **인증 및 접근 제어**: 회원가입/로그인 구현, 로그인 사용자만 챗봇 사용 가능.
  2. **FastAPI 웹 백엔드**: 서버 사이드 AI API 호출 (API 키 노출 방지), 타임아웃 방어 및 오류 안내.
  3. **대화 문맥 유지**: 최근 N개 대화 이력을 고려한 프롬프트 컨텍스트 주입.
  4. **대화 로그 영속화**: 사용자 식별, 시각, 질문, 응답, latency 등을 DB에 저장 및 조회/추적 API/스크립트 제공.
  5. **구조화된 로깅**: `request_received`, `ai_call_start`, `ai_call_success`, `db_save_success` 필수 이벤트 기록.
  6. **외부 접근성**: 평가 시 외부 접속 가능한 URL 제공 (ngrok / Cloud).
  7. **협업 및 형상관리**: main/develop 브랜치 전략, PR 머지 기록, 팀원별 10회 이상 커밋 이력.

---

## 2. 핵심 아키텍처 결정 내역 (Decision Records)

### [ADR-01] 프론트엔드 및 웹 연동 방식
- **결정**: **FastAPI Jinja2 템플릿 + TailwindCSS (CDN) + Vanilla JS**
- **대안 검토**: React/Vue SPA 별도 구성 (빌드 파이프라인 및 CORS 복잡도 증가)
- **선택 이유**:
  - 단일 Python 패키징으로 배포가 매우 간결함.
  - 브라우저 쿠키 기반 인증과 자연스럽게 연동됨.
  - 팀원들이 복잡한 Node.js 빌드 도구 없이 HTML/JS/CSS만으로 UI를 쉽게 수정하고 학습할 수 있음.

### [ADR-02] AI 모델 및 대화 문맥(Context) 전략
- **결정**: **Google Gemini API (`google-genai` 최신 SDK) + 최근 N개(5~10개) 롤링 윈도우 컨텍스트**
- **선택 이유**:
  - 최신 Gemini 모델(Gemini 2.5 Flash)의 빠른 응답 속도와 우수한 한국어 성능.
  - 최근 N개 대화 이력만 동적으로 추출하여 프롬프트에 주입함으로써 토큰 비용 및 응답 속도 최적화.
  - 타임아웃(Timeout) 및 API 장애 시 서버 크래시 없이 표준 에러 응답(`AI_TIMEOUT`) 반환 래퍼 적용.

### [ADR-03] 데이터베이스 및 ORM
- **결정**: **SQLite + SQLAlchemy 2.0 (ORM) + 조회/검증 CLI 스크립트**
- **선택 이유**:
  - SQLite는 별도의 DB 서버 설치 없이 단일 파일로 동작하여 로컬 개발, 평가자 검증, 이식성에 최적.
  - SQLAlchemy 2.0 최신 문법(Select/Session)을 사용하여 향후 PostgreSQL/MySQL로의 전환이 용이함.
  - `scripts/check_logs.py` 및 `scripts/check_logs.sql`을 제공하여 평가자 및 개발자가 즉시 DB 적재 상태를 검증 가능.

### [ADR-04] 사용자 인증 및 보안
- **결정**: **HTTP-Only Cookie 기반 JWT 인증 + Passlib(Bcrypt) 해싱**
- **선택 이유**:
  - XSS 공격에 안전하도록 자바스크립트에서 접근 불가능한 `HttpOnly` 쿠키 사용.
  - 일반 페이지 이동(SSR)과 비동기 Fetch 요청(AJAX) 모두에서 브라우저가 자동으로 쿠키를 전달하므로 클라이언트 코드가 매우 깔끔해짐.
  - 패스워드는 단방향 Bcrypt 솔팅 해시로 안전하게 저장.

### [ADR-05] 로깅 및 운영 모니터링
- **결정**: **Python 표준 `logging` + Request ID 상관관계 미들웨어 + 표준 이벤트 포맷**
- **선택 이유**:
  - 요청마다 고유한 `request_id` (UUID)를 발급하여 요청 수신부터 AI 호출, DB 저장까지 전 과정을 단일 ID로 추적.
  - 미션 평가 기준인 `request_received`, `ai_call_start`, `ai_call_success`, `db_save_success` 포맷 준수.

### [ADR-06] 협업 및 Antigravity 규칙 설정
- **결정**: **`.agents/rules/` 도입 및 모듈형 레이어드 아키텍처**
- **선택 이유**:
  - `.env` 및 시크릿이 Git에 절대 커밋되지 않도록 보안 규칙 자동화.
  - 기능별로 독립된 모듈(`api`, `core`, `models`, `schemas`, `services`, `templates`)을 구성하여 팀원들이 서로 충돌 없이 작업 분담 가능.

### [ADR-07] 실시간 스트리밍 응답 (SSE)
- **결정**: **Server-Sent Events (SSE) 기반 실시간 토큰 스트리밍 + 완료 시 DB 저장 및 Latency 측정**
- **선택 이유**:
  - 챗봇 사용자가 답변이 완전히 생성될 때까지 대기하지 않고, 실시간으로 타이핑되는 뛰어난 사용자 경험(UX) 제공.
  - 스트리밍 종료 시점에 전체 응답과 총 소요 시간(ms)을 계산하여 SQLite DB에 비동기 영속화.

### [ADR-08] 멀티 세션/스레드 대화방 관리
- **결정**: **사용자별 멀티 대화 세션 (1 User : N Sessions : N Messages) 지원**
- **선택 이유**:
  - 사용자가 주제별로 새로운 대화방을 만들고, 이전 대화 목록을 선택해 이어갈 수 있어 실제 ChatGPT와 동일한 경험 제공.
  - DB 관계형 모델링(User $\rightarrow$ ChatSession $\rightarrow$ ChatMessage)을 팀원들이 직접 실습하고 학습하기에 최적.

### [ADR-09] 외부 평가 URL 및 배포 지원
- **결정**: **원클릭 외부 공개 터널링 스크립트(`scripts/run_public.py`) + 무료 클라우드(Render/Fly.io) 배포 가이드 제공**
- **선택 이유**:
  - 평가 시 로컬 서버를 단 한 줄의 명령어로 안전한 공인 HTTPS URL로 즉시 외부에 노출 가능.
  - 클라우드 배포를 원하는 경우를 위한 Dockerfile 및 배포 절차 완비.

### [ADR-10] AI 페르소나 및 입력값 보안/제한 정책
- **결정**: **'AI/SW 개발 학습 튜터' 기본 시스템 프롬프트 + 최대 2,000자 입력 길이 제한 및 XSS 방지 Markdown 렌더링**
- **선택 이유**:
  - 본 미션(AI/SW 기초)의 학습 도우미로서 코드 문법 및 프로그래밍 개념을 친절하고 구조화된 마크다운(코드 블록)으로 답변.
  - 과도한 토큰 소모 및 비정상 요청을 방지하기 위해 1~2,000자 유효성 검사 적용.

### [ADR-11] 스마트 Mock/Demo 폴백 모드
- **결정**: **API 키 미설정 시 자동 Demo Mock 응답 모드 활성화 + 안내 배너 출력**
- **선택 이유**:
  - 팀원이 API 키를 아직 발급받지 않았거나 로컬 UI 및 라우트 테스트 시에도 서버 크래시 없이 학습 및 개발을 지속할 수 있도록 배려.

### [ADR-12] Git 브랜치 전략 및 협업 자동화 도구
- **결정**: **Git Flow 기반 브랜치 템플릿 및 자동화 스크립트(`scripts/setup_git_workflow.py`) 제공**
- **선택 이유**:
  - 미션 평가 기준인 `main`/`develop` 분리, `feature/*` 브랜치 작업, PR 기록 및 커밋 10회 이상 조건을 손쉽게 충족하고 팀원들과 실습할 수 있도록 지원.

### [ADR-13] Gemma 4 26B 모델 채택 및 환경변수 유연성
- **결정**: **Google AI Studio의 Gemma 4 26B(`gemma-4-26b-it`) 기본 모델 채택 + `.env`(`GEMINI_MODEL_NAME`) 동적 설정**
- **선택 이유**:
  - **26B vs 31B 비교**: 26B 모델은 31B에 비해 생성 속도(Tokens/sec)와 첫 토큰 응답 속도(TTFT)가 훨씬 빠르며, 무료/학습용 호출 할당량(Quota) 소모가 적어 실시간 웹 챗봇에 가장 이상적인 밸런스를 제공함.
  - `.env` 파일의 `GEMINI_MODEL_NAME` 환경변수를 통해 필요 시 언제든 다른 모델로 코드 수정 없이 즉시 전환 가능.

---

## 3. 데이터베이스 ERD 구조

```text
+------------------+       +---------------------+       +-----------------------+
|      users       |       |    chat_sessions    |       |     chat_messages     |
+------------------+       +---------------------+       +-----------------------+
| id (PK, Integer) |1     N| id (PK, Integer)    |1     N| id (PK, Integer)      |
| username (Str)   |<----->| user_id (FK, Users) |<----->| session_id (FK, Sess) |
| password_hash    |       | title (Str)         |       | user_id (FK, Users)   |
| created_at       |       | created_at          |       | role (user/assistant) |
| is_active (Bool) |       | updated_at          |       | content (Text)        |
+------------------+       +---------------------+       | latency_ms (Integer)  |
                                                         | status (success/err)  |
                                                         | error_message (Text)  |
                                                         | created_at            |
                                                         +-----------------------+
```

---

## 4. 팀원 역할 분담 제안 (Team Work Breakdown)

| 역할 분담 (예시) | 주요 담당 컴포넌트 | 세부 업무 내용 |
| :--- | :--- | :--- |
| **Member A (인증 및 보안)** | `app/api/v1/auth.py`<br>`app/core/security.py`<br>`app/models/user.py` | 회원가입, 로그인/로그아웃, 패스워드 Bcrypt 암호화, JWT 검증 미들웨어 및 의존성 주입 |
| **Member B (AI 파이프라인)** | `app/services/gemini_service.py`<br>`app/api/v1/chat.py` | Google Gemini API 연동, SSE 스트리밍 응답, 최근 N개 대화 문맥 조립, Mock 모드 및 타임아웃 래퍼 |
| **Member C (DB 및 로깅/운영)** | `app/models/chat.py`<br>`app/core/logging.py`<br>`scripts/` | 세션 및 메시지 ORM 모델링, Request ID 추적 미들웨어, DB 로그 검증 스크립트(`check_logs.py`) |
| **Member D (UI 및 배포/협업)** | `app/templates/`<br>`app/static/`<br>`scripts/run_public.py`<br>`scripts/setup_git_workflow.py` | 사이드바 멀티세션 UI, 실시간 SSE 스트리밍 렌더링, 로그 뷰어 화면, 외부 터널링 및 Git 협업 셋업 |
