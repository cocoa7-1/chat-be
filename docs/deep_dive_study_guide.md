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
