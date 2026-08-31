# 🔬 건설 안전 & 시공 AI 챗봇: 초정밀 현미경 학습 가이드 및 마스터 로드맵

> **문서 목적**: 본 가이드는 [AI/SW 기초 텀프로젝트] 미션 요구사항과 본 프로젝트(`chat-be` & `chat-fe`)의 실제 코드베이스 간의 정합성을 1:1로 매핑하여, 시스템의 모든 레이어를 분해하고 체계적으로 학습하기 위해 작성된 종합 엔지니어링 가이드입니다.

---

## 🧭 [Part 1] 미션의 본질적 함의와 아키텍처 정합성

### 1.1 왜 단순한 'AI API 호출'이 아닌 '웹 서비스'인가?
단순히 터미널에서 LLM API를 호출하는 것은 수십 줄의 코드로 가능합니다. 하지만 **실제 사용자가 접속하여 사용하는 엔터프라이즈급 AI 챗봇 서비스**는 다음의 복합적인 엔지니어링 과제를 해결해야 합니다:

```
[클라이언트 (chat-fe) - Vercel]
       │  ▲  (HTTP Request / SSE Token Stream)
       ▼  │
[FastAPI 웹 서버 (chat-be) - AWS EC2] ── (Request ID 추적 & 지연시간 측정 미들웨어)
       │
       ├── [보안/인증 계층 (Role 1)]: Bcrypt 해시 검증 + Bearer/Cookie JWT 토큰 검증
       ├── [세션/상태 관리 (Role 3)]: 멀티 세션 CRUD + 최근 10개 롤링 윈도우 컨텍스트 조립
       ├── [AI 스트리밍 계층 (Role 3)]: Google Gemma 4 26B 비동기 스트리밍 + 30초 타임아웃 방어 + Mock 폴백
       ├── [관측/로깅 계층 (Role 2)]: 4대 필수 이벤트(수신, AI호출, AI완료, DB저장) 구조화 로깅
       └── [데이터 영속화 (Role 2)]: SQLite + SQLAlchemy 2.0 ORM (사용자, 세션, 메시지, 지연시간)
```

### 1.2 미션 요구사항 vs 구현 결과 정합성 매트릭스

| 미션 요구 영역 | 미션 명세 세부 요건 | 실제 구현 파일 및 함수 | 정합성 검증 결과 |
| :--- | :--- | :--- | :---: |
| **웹 UI & 스트리밍** | 질문 입력, 동일 화면 답변 확인, 실시간 토큰 스트리밍 | `chat-fe/index.html`, `app/api/v1/chat.py` | **100% 충족** (`text/event-stream` SSE) |
| **사용자 인증 & 보안** | 계정 생성, 로그인, 인증 기반 접근 제어 | `app/core/security.py`, `app/api/deps.py` | **100% 충족** (Bcrypt + JWT Bearer) |
| **대화 문맥 유지** | 이전 대화 질문/답변 고려한 연속 대화 | `gemini_service._build_context_messages` | **100% 충족** (최근 10개 롤링 윈도우) |
| **안정성 & 타임아웃** | AI API 타임아웃(30초) 및 실패 시 친절한 에러 안내 | `gemini_service.stream_chat_response` | **100% 충족** (`AI_TIMEOUT`, Mock Fallback) |
| **구조화된 로깅** | 4대 필수 이벤트(수신, 호출, 완료, 저장) 기록 | `app/core/logging.py`, `app/core/middlewares.py` | **100% 충족** (Request ID 연계 로거) |
| **대화 로그 영속화** | 질문, 응답, 지연시간(ms), 상태 DB 저장 | `app/models/chat.py`, `ChatMessage` | **100% 충족** (SQLite ORM 매핑) |
| **로그 검증 도구** | 평가자가 로그를 확인하는 Web UI / CLI / SQL 3종 | `chat-fe/logs.html`, `check_logs.py`, `check_logs.sql` | **100% 충족** (3종 검증 도구 완비) |
| **외부 네트워크 접속** | 평가 시점에 외부에서 접속 가능한 URL 제공 | `scripts/run_public.py`, Vercel + AWS EC2 배포 | **100% 충족** (Vercel URL & 터널링 도구) |
| **형상관리 & 협업** | Git Flow 브랜치, PR 이력, 10회 이상 커밋 | `main`, `develop`, `dev/auth`, `dev/log`, `dev/chat` | **100% 충족** (역할별 브랜치 분리) |

---

## 🔬 [Part 2] 4인 팀 역할 분담 및 마스터 로드맵

```text
main (배포 안정 버전)
  │
develop (통합 개발 베이스라인)
  ├── dev/auth      (Role 1: 인증 및 보안 모듈)
  ├── dev/log       (Role 2: DB ORM 모델링 & 로깅 - 질문자 본인)
  ├── dev/chat      (Role 3: AI 스트리밍 & 타임아웃)
  └── dev/frontend  (프론트엔드 UI & Vercel 배포)
```

- **👑 감독 (Director)**: 아키텍처 검토, PR 리뷰 및 머지, 브랜치 관리, AWS EC2 배포 및 인프라 총괄.
- **🛡️ Role 1 (인증/보안 엔지니어)**: Bcrypt 해싱, JWT 발급/검증, 인증 의존성(`deps.py`) 구현, 건설 안전 도메인 연계.
- **💾 Role 2 (데이터/로깅 엔지니어)**: SQLAlchemy 2.0 모델링, Request ID 미들웨어, 4대 구조화 로거, `check_logs.py`/`check_logs.sql` 작성.
- **🤖 Role 3 (AI 파이프라인 엔지니어)**: Google AI Studio Gemma 4 26B API 연동, SSE 스트리밍 청크 제어, 30초 타임아웃 및 스마트 Mock 폴백 로직 구현.
- **🌐 프론트엔드 (UI 엔지니어)**: TailwindCSS 반응형 화면, SSE 실시간 렌더링(`chat.js`), 대화 로그 검증 센터(`logs.html`), Vercel 배포.

---

## 🎯 [Part 3] 핵심 실습 과제 (Hands-on Practice)

1. **타임아웃 한계치 튜닝 실험**: `.env`의 `AI_TIMEOUT_SECONDS=1`로 줄인 뒤 질문하여 `AI_TIMEOUT` 배너가 화면에 정상 출력되는지 확인.
2. **Raw SQL 대화 로그 분석**: `python scripts/check_logs.py`를 실행하여 SQLite DB에 적재된 질문/답변/지연시간(ms) 확인.
3. **건설 도메인 시스템 프롬프트 수정**: `.env`의 `SYSTEM_INSTRUCTION`을 수정하여 챗봇의 전문 분야 말투 변화 관찰.

---

## 🧠 [Part 4] 실전 질의응답 및 누적 학습 노트 (Compounding Q&A Knowledge Base)

> **원칙**: 본 섹션은 개발 과정에서 팀원이 실제로 궁금해하고 탐구한 핵심 질문과 기술적 해답을 지속적으로 누적(Compounding)하는 단일 진실 공급원(SSOT)입니다.

### [Q1] Git 브랜치(Branch) 개념과 왜 GitHub 웹 `main`에 구버전이 보였는가?
- **핵심 원리**: Git에서 브랜치는 코드의 복사본이 아니라, 특정 커밋 해시를 가리키는 **'41바이트짜리 텍스트 포인터 파일'**(`.git/refs/heads/<branch_name>`)에 불과합니다.
- **현상 원인**:
  - `dev/log` 브랜치에 최신 커밋을 푸시했더라도, `main` 브랜치 포인터는 과거 커밋(`ab63f09`)에 머물러 있었습니다.
  - GitHub 웹페이지의 기본 뷰(Default View)가 `main`으로 설정되어 있었기 때문에, 상단 브랜치를 `develop`이나 `dev/log`로 전환하지 않으면 구버전 README/ADR이 노출되었던 것입니다.
- **해결 및 예방**: 작업 완료 후 `dev/log -> develop -> main` 순으로 순차 머지(PR)를 진행하여 상위 브랜치 포인터를 최신화합니다.

### [Q2] PR(Pull Request)과 PR 템플릿의 의미, 그리고 팀 승인의 본질
- **PR의 본질**: "내가 작업한 브랜치의 코드를 상위 브랜치(`develop` 또는 `main`)로 가져가서(Pull) 합쳐달라고 요청(Request)하는 협업 티켓"입니다.
- **PR 템플릿(`.github/pull_request_template.md`)**:
  - 개발자가 PR을 생성할 때 본문 작성창에 자동으로 채워지는 **'품질 보증 설문 양식'**입니다.
  - 핵심 항목: `어떤 기능인가요?`, `작업 상세 내용`, `내가 설명할 수 있는 부분(Self-explanation)`, `아직 이해 못 한 부분`, `새로 알게 된 것`.
- **승인(Approve)의 주체**: 작업자 본인이 승인하는 것이 아니라, PR을 올린 뒤 **코드 리뷰어(감독/동료)**가 코드를 검토하고 승인(Approve) 및 머지(Merge) 버튼을 누르는 것이 올바른 팀 협업 절차입니다.

### [Q3] FastAPI 전체 요청 수명주기 (Request Lifecycle 10단계)
- **전체 흐름 시퀀스**:
  1. `Client`가 `GET /api/v1/logs?limit=50` (헤더에 Bearer JWT 토큰 포함) 전송.
  2. `Uvicorn`(ASGI 비동기 서버)이 TCP 소켓 연결을 수신하여 FastAPI 앱에 이벤트 전달.
  3. `Request ID 미들웨어`(`middlewares.py`)가 요청마다 고유 UUID를 발급하고 `request_received` 로그 출력.
  4. 라우터 진입 직전 `Depends(get_current_user)`가 실행되어 JWT 토큰의 유효성 검증 및 서명 해독.
  5. `Depends(get_db)`가 실행되어 SQLAlchemy SQLite 세션(`db`)을 생성하여 라우터 함수 인자로 주입.
  6. `logs.py` 라우터 함수가 `select(ChatMessage)` 및 `select(func.count())` ORM 쿼리를 SQLite DB에 전송.
  7. SQLite DB(`chatbot.db`)가 파일 I/O를 통해 레코드를 읽어 ORM 인스턴스로 반환.
  8. `logs.py`가 데이터를 `ChatLogsResponse` (Pydantic DTO) 규격으로 직렬화.
  9. 응답 반환 시 미들웨어가 HTTP 응답 헤더에 `X-Request-ID`를 첨부.
  10. `Client`가 HTTP 200 OK와 함께 검증된 JSON 데이터를 수신하여 UI 렌더링.

### [Q4] `requirements.txt` vs `uv` 패키지 관리의 역할 분담
- **질문**: "`uv`를 쓰는데 `requirements.txt`가 왜 여전히 필요한가요?"
- **해답**:
  - `requirements.txt`는 파이썬 생태계의 **"표준 의존성 명세서(Specification Sheet)"**입니다.
  - `uv`는 그 명세서를 버리는 것이 아니라, **명세서를 10~100배 빠른 속도로 설치해주는 '초고속 실행 엔진'(`uv pip install -r requirements.txt`)**입니다.
  - 팀원 중 `uv`가 없는 개발자나 AWS EC2/클라우드 배포 스크립트(`pip install -r requirements.txt`)와의 100% 호환성을 보장하기 위해 `requirements.txt`는 단일 진실 공급원(SSOT)으로 반드시 유지해야 합니다.

### [Q5] 4대 표준 로깅 이벤트와 지연시간(Latency) 추적 원리
- **4대 필수 이벤트**:
  1. `request_received`: 요청 수신 시각, 경로, 클라이언트 IP, `request_id` 기록.
  2. `ai_call_start`: Google Gemma 4 26B API 호출 직전 타임스탬프 기록.
  3. `ai_call_success` (또는 `ai_call_error`): 스트리밍 완료 후 총 소요 시간(`latency_ms`) 및 토큰 수 기록.
  4. `db_save_success`: DB에 질문/답변/지연시간 레코드가 커밋된 직후 기록.
- **지연시간 측정 공식**:
  $$\text{latency\_ms} = (\text{time}_{\text{end}} - \text{time}_{\text{start}}) \times 1000$$
- **가치**: 분산 시스템에서 특정 질문의 병목 구간이 네트워크인지, AI 추론인지, DB 쓰기인지 `request_id` 하나로 단숨에 추적(Distributed Tracing) 가능.

### [Q6] SQLite 동시성 락(`database is locked`) 방어 원리
- **원인**: SQLite는 파일 기반 DB이므로 쓰기(Write) 작업 시 파일 전체에 배타적 락(Exclusive Lock)을 겁니다.
- **방어 메커니즘**:
  - `app/core/database.py`에서 `connect_args={"check_same_thread": False, "timeout": 30}`을 설정하여, 동시 쓰기 경합 시 즉시 에러를 내지 않고 최대 30초간 대기(Wait Queue) 후 순차 커밋하도록 보장합니다.

