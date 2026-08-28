# 💾 Role 2: 데이터 & 로깅 (DB & Logging) 담당자 가이드

본 문서는 **SQLite 데이터베이스 모델링, 대화 이력 영속화, 구조화된 애플리케이션 로깅 및 로그 검증 도구**를 담당하는 팀원을 위한 개발 및 분석 가이드입니다.

---

## 📌 1. 담당 영역 및 핵심 파일

| 구분 | 파일 경로 | 설명 |
| :--- | :--- | :--- |
| **API 라우터** | `app/api/v1/logs.py` | 사용자별 대화 로그 조회 (`GET /api/v1/logs`), 통계 API |
| **DB 설정/세션** | `app/core/database.py` | SQLite 엔진 생성, `Base` 선언, `get_db` 세션 제너레이터 |
| **로깅 시스템** | `app/core/logging.py` | 표준 규격 로그 포맷터 (`request_received`, `ai_call_start` 등) |
| **미들웨어** | `app/core/middlewares.py` | 요청마다 UUID `request_id` 발급 및 추적 미들웨어 |
| **데이터 모델** | `app/models/chat.py` | `ChatSession` (대화방) 및 `ChatMessage` (메시지/지연시간/상태) ORM 모델 |
| **검증 스크립트** | `scripts/check_logs.py` | 터미널에서 즉시 최근 DB 대화 로그 및 통계를 조회하는 CLI 도구 |
| **검증 SQL** | `scripts/check_logs.sql` | SQLite CLI에서 직접 실행 가능한 표준 SQL 쿼리문 |
| **단위 테스트** | `tests/test_db.py` | 세션/메시지 CRUD 및 관계형 무결성 테스트 |

---

## 🗄️ 2. 데이터베이스 스키마 구조 (ERD)

```
[ users ] (1)
   │
   └──< (N) [ chat_sessions ] (1)
               │
               └──< (N) [ chat_messages ]
```

### 테이블 상세 정의 (`app/models/chat.py`)
- **`chat_sessions`**:
  - `id` (INTEGER, PK, Auto-Increment)
  - `user_id` (INTEGER, FK -> users.id)
  - `title` (VARCHAR(200)): 첫 질문 기반 요약 제목
  - `created_at`, `updated_at` (DATETIME)
- **`chat_messages`**:
  - `id` (INTEGER, PK, Auto-Increment)
  - `session_id` (INTEGER, FK -> chat_sessions.id)
  - `user_id` (INTEGER, FK -> users.id)
  - `role` (VARCHAR(20)): `'user'` 또는 `'assistant'`
  - `content` (TEXT): 질문 또는 AI 답변 본문
  - `latency_ms` (INTEGER): AI 응답 생성 소요 시간 (밀리초)
  - `status` (VARCHAR(20)): `'success'`, `'error'`, `'timeout'`
  - `created_at` (DATETIME)

---

## 📝 3. 구조화된 로그 이벤트 규격 (`app/core/logging.py`)

미션 평가 및 운영 모니터링을 위해 다음 4가지 핵심 이벤트를 일관된 포맷으로 출력합니다:

1. **`request_received`**: API 요청 수신 시 (`user_id`, `path`, `request_id`)
2. **`ai_call_start`**: AI API(Gemini) 호출 시작 시 (`request_id`, `model`)
3. **`ai_call_success`**: AI API 정상 응답 수신 시 (`request_id`, `latency_ms`)
4. **`db_save_success`**: 대화 메시지가 SQLite DB에 안전하게 커밋되었을 때 (`chat_id`, `session_id`)

---

## 🧪 4. 테스트 및 검증 방법

### 1) 자동화 테스트 실행
```bash
pytest tests/test_db.py -v
```

### 2) CLI 검증 스크립트 실행
서버에서 채팅이 이루어진 후, 터미널에서 아래 명령어로 DB에 적재된 로그를 검증합니다:
```bash
python scripts/check_logs.py
```

### 3) SQL 직접 쿼리 검증
```bash
# Windows PowerShell / CMD
sqlite3 chatbot.db ".read scripts/check_logs.sql"
```
