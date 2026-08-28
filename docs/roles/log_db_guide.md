# 💾 Role 2: 데이터 & 로깅 (DB & Logging) 담당자 완벽 가이드

> **환영합니다!** 본 문서는 **SQLite 데이터베이스 모델링, 대화 이력 영속화, 4대 핵심 구조화 로깅, 통계 집계 및 CLI/SQL 검증 도구**를 완벽하게 정복하기 위한 실전 가이드입니다.

---

## 🌟 1. 이 파트의 본질적 의미와 중요성 (Why this matters)

AI 챗봇 서비스에서 **데이터베이스와 로깅은 서비스의 '블랙박스'이자 '기억 장치'**입니다.

1. **대화 이력을 DB에 저장해야 하는 이유**
   - 사용자가 페이지를 새로고침하거나 며칠 뒤 다시 접속했을 때 이전 대화 맥락을 그대로 복원하고, AI에게 이전 대화를 주입(Multi-turn Context)하기 위해 필수적입니다.
2. **지연시간(`latency_ms`)과 상태(`status`)를 기록하는 이유**
   - AI API가 평균 몇 초 만에 응답하는지, 어떤 질문에서 타임아웃이나 에러가 발생하는지 모니터링하여 시스템 품질을 지속적으로 개선할 수 있습니다.
3. **구조화된 4대 표준 로그 이벤트의 힘**
   - 단순한 텍스트 출력이 아니라 `request_id`, `user_id`, `latency_ms`가 포함된 구조화된 로그는 실무에서 대규모 분산 시스템을 추적(Distributed Tracing)하는 핵심 기반입니다.

---

## 📂 2. 내가 맡은 핵심 파일 및 디렉토리 구조

| 파일 경로 | 핵심 역할 | 내가 주로 만질 부분 |
| :--- | :--- | :--- |
| `app/api/v1/logs.py` | 대화 로그 조회 및 통계 API | 사용자별 로그 페이징, 통계 집계 로직 |
| `app/core/database.py` | SQLite 엔진 및 SQLAlchemy 세션 제너레이터 | DB 연결 풀, 세션 관리 (`get_db`) |
| `app/core/logging.py` | 4대 표준 로그 이벤트 포맷터 | 로그 출력 포맷, 색상, 파일 로깅 |
| `app/core/middlewares.py` | 요청별 고유 UUID `request_id` 발급 미들웨어 | HTTP 헤더 및 로깅 컨텍스트 주입 |
| `app/models/chat.py` | `ChatSession` 및 `ChatMessage` ORM 모델 | 테이블 컬럼 및 외래키(FK) 관계 설정 |
| `scripts/check_logs.py` | 터미널용 DB 로그 검증 CLI 도구 | 예쁜 터미널 테이블 출력, 메트릭 집계 |
| `scripts/check_logs.sql` | SQLite 직접 쿼리용 표준 SQL 스크립트 | SELECT 쿼리, 통계 GROUP BY 쿼리 |
| `tests/test_db.py` | DB 모델 관계 및 CRUD 단위 테스트 | 세션-메시지 종속 삭제, 롤백 테스트 |

---

## 🚀 3. 당장 5분 만에 시작하는 체크리스트

```bash
# 1. 내 브랜치로 이동
git checkout dev/log

# 2. 내 파트 테스트 실행해보기
pytest tests/test_db.py -v

# 3. CLI 로그 검증 도구 실행해보기 (DB에 저장된 실제 데이터 확인!)
python scripts/check_logs.py
```

---

## 🛠️ 4. 단계별 손쉬운 실습 과제 4단계 (Hands-on Experiments)

### 🟢 Level 1: `scripts/check_logs.py`의 출력 포맷 커스텀하기
- **파일**: `scripts/check_logs.py`
- **목표**: 터미널 출력에 이모지(👷, 🤖, ⏱️)를 추가하고, 지연시간이 3초(3000ms) 이상인 경우 노란색/빨간색 경고 표시 붙이기

### 🟡 Level 2: 특정 세션의 대화 로그만 필터링하는 쿼리 및 API 확장
- **파일**: `app/api/v1/logs.py`
- **목표**: `GET /api/v1/logs?session_id=1` 쿼리 파라미터를 추가하여 특정 대화방의 로그만 골라볼 수 있도록 기능 추가

### 🟠 Level 3: 대화 통계 요약 엔드포인트(`GET /api/v1/logs/stats`) 만들기
- **파일**: `app/api/v1/logs.py`, `app/schemas/chat.py`
- **목표**: 로그인한 사용자의 총 대화 수, 총 세션 수, 평균 AI 응답 시간(ms), 성공률(%)을 계산하여 반환하는 통계 API 개발

### 🔴 Level 4: `scripts/check_logs.sql`에 실무 SQL 쿼리 추가하기
- **파일**: `scripts/check_logs.sql`
- **목표**: 가장 질문을 많이 한 상위 사용자 TOP 5, 시간대별 질문 건수 집계 SQL 작성

---

## 📝 5. 10회 이상 의미 있는 커밋(Commit) 분할 레시피

1. `feat(db): Add check_logs CLI formatting with latency color badges`
2. `feat(logs): Add session_id query parameter filter in GET /logs`
3. `test(db): Add unit test for filtered log queries`
4. `feat(logs): Implement user chat statistics endpoint (GET /logs/stats)`
5. `test(logs): Add test case for chat statistics calculations`
6. `refactor(logging): Enhance structured log formatting for db_save_success event`
7. `feat(sql): Add advanced analytical queries to check_logs.sql`
8. `docs(db): Document SQLite schema ERD and query optimization notes`
9. `refactor(db): Add index on ChatMessage(user_id, created_at) for fast retrieval`
10. `test(db): Ensure full coverage of cascade deletes and session integrity`

---

## ❓ 6. 자주 겪는 오류 및 해결책 (Troubleshooting)

- **`sqlite3.OperationalError: database is locked`**:
  - SQLite는 여러 프로세스가 동시에 쓸 때 락이 걸릴 수 있습니다. `app/core/database.py`에서 `connect_args={"check_same_thread": False, "timeout": 30}` 옵션이 잘 설정되어 있는지 확인하세요.
