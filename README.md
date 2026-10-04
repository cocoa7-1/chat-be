# 건설 도메인 지식·상식 Q&A 챗봇 — chat-be

건설 용어와 절차가 익숙하지 않은 사용자가 회원가입·로그인 후 질문하고, AI 답변과 이전 대화를 확인하는 웹 챗봇의 FastAPI 백엔드입니다. 시공·공정, 인허가, 계약·비용, 참여 주체, 자재·구조, 개념 비교, 플랜트 분야를 다룹니다. 학습용 정보 제공을 목표로 하며 현장 판단을 대체하지 않습니다.

- 백엔드: https://github.com/cocoa7-1/chat-be
- 프론트엔드: https://github.com/cocoa7-1/chat-fe
- 배포 목표: 정적 프론트 Vercel + 백엔드 AWS EC2 한 대 + SQLite
- 프론트 Production: https://b7-1-chat-fe.vercel.app
- 백엔드 HTTPS / API 문서: https://b71chatbe.ddns.net / https://b71chatbe.ddns.net/docs
- 배포 연결 상태: 2026-10-04 Codex가 공개 FE 파일·BE healthy/production·실제 FE Origin CORS 응답 확인. 사용자가 배포 브라우저에서 가입·로그인·Demo 질문·로그 재조회 후, 서버에 AI 키를 직접 설정하고 실제 AI 답변·연속 질문 문맥·질문/답변 로그를 확인했습니다. 사용자 시험 결과와 Codex 직접 HTTP 검증은 구분합니다.
- 배포 기능 기준: `4ce07e4`. 전체 AI 스트림 타임아웃과 초기 DB 저장 처리는 `dev/log-mission-docs`에서 보완했으며 [PR #10](https://github.com/cocoa7-1/chat-be/pull/10)에서 리뷰합니다. 서버 반영은 별도 단계입니다. 2026-10-04 GitHub 확인 당시 PR #10은 open, 대상 develop, 리뷰 요청자 dolphin1404였습니다.

## 핵심 시나리오와 구조

회원가입 → 로그인·JWT 발급 → 질문 입력 → 사용자·세션 확인 → 질문 DB 저장 → 최근 대화와 현재 질문을 AI에 전달 → SSE 답변 전송 → 답변 DB 저장 → 내 대화·로그 조회 흐름입니다.

```text
브라우저 ── HTTPS ── Vercel (chat-fe: HTML/CSS/JS)
    └────── HTTPS ── EC2 / Caddy ── FastAPI / Uvicorn
                                      ├─ SQLite
                                      └─ Google AI API (키는 서버에만 보관)
```

Python 3.12, FastAPI, SQLAlchemy, SQLite, Google GenAI SDK를 사용합니다. 비밀번호는 bcrypt 해시로 저장하고 JWT를 발급합니다. 프론트는 `Authorization: Bearer` 헤더를 전송하며 백엔드는 HttpOnly 쿠키 인증도 지원합니다.

AI 키가 없거나 SDK 클라이언트 초기화가 실패하면 **Mock 응답**으로 동작합니다. Mock는 연결 시험용이며 실제 AI 호출·대화 문맥 유지 검증을 대신하지 않습니다. 실제 AI에는 최근 `MAX_HISTORY_MESSAGES`개 메시지를 전달합니다. 현재 설정 모델은 `gemma-4-26b-a4b-it`이며 해당 Google 프로젝트의 모델 접근·무료 할당량을 확인해야 합니다.

## 로컬 실행과 환경 변수

레포 루트에서 실행합니다. 아래는 `uv` 설치 환경 기준입니다.

```bash
uv venv --python 3.12
uv pip install -r requirements.txt
# Linux / macOS
cp .env.example .env
```

Windows PowerShell의 파일 복사는 `Copy-Item .env.example .env`를 사용합니다.

실제 읽는 이름은 **`SECRET_KEY`, `ALGORITHM`**입니다. `JWT_SECRET_KEY`, `JWT_ALGORITHM`은 이 코드에서 읽지 않습니다. 설정에 없는 이름은 무시되므로 정확한 이름을 사용합니다.

| 환경 변수 | 용도 / 기본값 |
|---|---|
| `APP_NAME` | 서비스 표시 이름 |
| `APP_ENV` | 로컬 `development`, 배포 `production` |
| `DEBUG` | 로컬 true, 배포 false. 다른 보안 설정을 자동 변경하지 않음 |
| `HOST`, `PORT` | `python -m app.main`의 주소·포트. Uvicorn CLI 실행은 CLI 옵션으로 지정 |
| `SECRET_KEY` | JWT 서명 키. 개발용 예제 값을 실제 배포에 사용하지 않음 |
| `ALGORITHM` | JWT 알고리즘, `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 토큰 유효 시간, `1440`분 |
| `COOKIE_NAME` | 인증 쿠키 이름, `access_token` |
| `DATABASE_URL` | 로컬 `sqlite:///./chatbot.db`, 배포는 보존할 파일의 절대 경로 권장 |
| `GEMINI_API_KEY` | 서버 전용 AI API 키. 빈 값이면 Mock |
| `GEMINI_MODEL_NAME` | AI 모델 ID, 기본 `gemma-4-26b-a4b-it` |
| `AI_TIMEOUT_SECONDS` | 연결 시작부터 응답 스트림 완료까지 공유하는 전체 제한, 기본 `30`초. SDK 스트림 정리는 별도로 최대 1초 |
| `MAX_HISTORY_MESSAGES` | 실제 AI에 전달할 최근 메시지 수, `10`개 (질문·답변 각각 한 메시지) |
| `SYSTEM_INSTRUCTION` | 선택: 건설 도메인 시스템 지시문 재정의. 생략 시 코드 기본값 사용 |
| `REGISTER_REQUESTS_PER_MINUTE` | IP당 최근60초 가입 요청, 기본5회 |
| `LOGIN_REQUESTS_PER_MINUTE` | IP당 최근60초 로그인·비밀번호 변경 요청 합산, 기본10회 |
| `CHAT_REQUESTS_PER_MINUTE` | 사용자당 최근60초 채팅 요청, 기본6회 |
| `CHAT_GLOBAL_REQUESTS_PER_MINUTE` | 프로세스 전체 최근60초 채팅 요청, 기본20회 |
| `CHAT_USER_CONCURRENCY`, `CHAT_GLOBAL_CONCURRENCY` | 진행 중 채팅 사용자당1개·전체3개 |

JWT 키는 사용자가 직접 생성한 충분한 랜덤값을 `.env`의 `SECRET_KEY`에만 넣습니다. `APP_ENV=production/prod`에서는 공개 개발 기본값·빈 값·32바이트 미만의 키로 서버를 시작할 수 없습니다. 기존 키를 자동 교체하지 않습니다. `.env`, DB, 로그는 `.gitignore`에 포함됩니다. AI 키·JWT 키·로그인 토큰 원문을 대화·로그·프론트 JS·Git에 넣지 않습니다.

```bash
uv run uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

- 상태 확인: http://localhost:8000/
- API 명세·요청 실행: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

프론트 레포는 `python -m http.server 3000`으로 실행하고 http://localhost:3000/ 에 접속합니다. 로컬 API 주소는 `http://localhost:8000`입니다. FE `dev/log-frontend-integration`에서 nickname 입력·전송과 배포 API 주소 분리를 수정했습니다. 배포에는 해당 수정이 반영된 브랜치를 사용하고 `js/config.js`의 `DEPLOYED_API_BASE_URL`에 실제 백엔드 HTTPS 주소를 입력합니다. [미션 점검표](docs/mission-checklist.md)를 참고하세요.

## API 명세

인증 요청은 `Authorization: Bearer <로그인 응답의 access_token>`을 전송합니다. 아래는 전체 경로이며 상세 필드 정의는 `/docs`에서 확인합니다.

| 메서드 | 경로 | 인증 | 기능 |
|---|---|---|---|
| GET | `/` | 불필요 | 서버 상태 |
| POST | `/api/v1/auth/register` | 불필요 | 회원가입 |
| POST | `/api/v1/auth/login` | 불필요 | 로그인·토큰 발급 |
| POST | `/api/v1/auth/logout` | 불필요 | 인증 쿠키 삭제. 프론트 토큰은 프론트에서 삭제 |
| GET | `/api/v1/auth/me` | 필요 | 현재 사용자 |
| PUT | `/api/v1/auth/password` | 필요 | 비밀번호 변경 |
| GET / POST | `/api/v1/chat/sessions` | 필요 | 내 세션 목록 / 세션 생성 |
| DELETE | `/api/v1/chat/sessions/{session_id}` | 필요 | 내 세션·메시지 삭제 |
| GET | `/api/v1/chat/sessions/{session_id}/messages` | 필요 | 내 세션 메시지 조회 |
| POST | `/api/v1/chat/stream` | 필요 | 질문·SSE 답변 |
| GET | `/api/v1/logs` | 필요 | 내 로그·페이지네이션 |
| GET | `/api/v1/logs/stats` | 필요 | 내 질문·답변·지연시간 통계 |

### 회원가입과 로그인

`POST /api/v1/auth/register` 요청:

```json
{"username":"demo_user","nickname":"학습자","password":"examplePassword123!"}
```

HTTP 201 응답 예시:

```json
{"id":1,"username":"demo_user","nickname":"학습자","is_active":true,"is_admin":false,"created_at":"2026-10-04T00:00:00"}
```

`POST /api/v1/auth/login` 요청:

```json
{"username":"demo_user","password":"examplePassword123!"}
```

HTTP 200으로 `access_token`, `token_type: "bearer"`, `user`를 반환합니다. 실제 토큰은 문서에 저장하지 않습니다. 가입은 닉네임 필수·비밀번호 8자 이상입니다. 중복 아이디는 400, 로그인 실패는 401, 입력 검증 실패는 422입니다.

### 질문과 SSE 응답

`POST /api/v1/chat/stream` 요청 (`session_id` 생략 시 새 세션 생성):

```json
{"message":"감리와 감독의 차이를 설명해 줘.","session_id":1}
```

응답은 JSON 한 개가 아닌 `text/event-stream`입니다:

```text
event: meta
data: {"session_id":1,"session_title":"건설 질문","user_message_id":1,"request_id":"example"}

data: {"text":"감리는 "}

data: {"text":"..."}

event: done
data: {"done":true,"message_id":2,"latency_ms":1200,"status":"success","error":null}
```

질문은 공백만 입력할 수 없고 최대 2,000자입니다. 비로그인은 401입니다. 스트림 시작 후 AI 오류가 생기면 HTTP 상태는 이미 200일 수 있으므로 답변의 오류 안내와 완료 이벤트의 `error`를 확인합니다. 연결 또는 응답 읽기가 전체 제한을 넘으면 `AI_TIMEOUT`, 기타 AI 오류는 `AI_SERVICE_ERROR`, 스트림 내부 서버 오류는 `event: error`로 안내합니다. 타임아웃 전 받은 답변 일부와 오류 안내도 `status=error`, `error_message=AI_TIMEOUT`으로 저장됩니다.

스트림 이전 세션·질문 저장 또는 명시적 세션 생성이 실패하면 SSE를 시작하지 않고 HTTP 500과 아래 JSON을 반환합니다. 자동 생성 세션과 질문은 한 트랜잭션으로 저장하므로 질문 저장 실패 시 새 세션도 되돌립니다.

```json
{"detail":"대화를 저장하지 못했습니다. 잠시 후 다시 시도해 주세요."}
```

세션·사용자 질문은 AI 호출 전에 저장을 완료합니다. AI 오류나 타임아웃은 이미 저장한 질문을 되돌리지 않습니다. AI 답변 또는 오류 안내는 이후 별도 저장 단계이며, 답변 저장 자체가 실패해도 앞서 저장한 질문은 남습니다. 초기 DB 저장 자체가 실패한 질문은 저장된 것으로 처리하지 않고 위 오류 안내를 반환합니다.

### 요청 남용 제한과 운영 점검

가입·로그인 실패도 IP별 횟수에 포함합니다. 채팅은 사용자별·전체 최근60초 횟수 및 동시 요청 수를 함께 검사하며 초과하면 HTTP429, 고정 안내 JSON, `Retry-After` 헤더와 `request_rejected` 이벤트를 반환합니다. 거절된 채팅은 질문 저장·AI 호출을 하지 않습니다. 동시 슬롯은 DB 처리부터 SSE 전송 종료까지 유지하고 정상 종료·실패·클라이언트 취소 시 해제합니다. 이미 저장된 질문을 제한 때문에 삭제하지 않습니다.

기존 `--workers 1` 배포에 맞춘 메모리 제한입니다. 프로세스 재시작 때 횟수가 초기화되며 여러 프로세스/인스턴스 사이에 공유되지 않습니다. 오래된 집계는 만료시키고 집계 키를 최대10,000개로 제한합니다. 제한은 사용량 남용을 줄이는 장치이며 AWS·Google의 청구 한도는 아닙니다. 현재 FE는429를 일반 요청 오류로 표시합니다.

IP는 ASGI client 주소를 사용하며 앱에서 사용자가 보낸 `X-Forwarded-For`를 직접 신뢰하지 않습니다. 운영에서는8000을 외부에 열지 않고 Uvicorn이 loopback Caddy만 신뢰하는지 확인해야 합니다. CORS 제한만으로 직접 자동화 요청이 막히지는 않습니다.

Aside가 기존 서비스 PID를 확인한 뒤 같은 Python 환경에서 `scripts/check_security_config.py --pid <PID>`를 실행하면 현재 프로세스 환경과 작업 폴더의 설정을 기준으로 JWT 설정 여부·개발 기본값과 다른지·최소 길이·production 여부를 boolean으로만 출력합니다. 키 원문·해시·환경변수 전체를 출력하거나 DB/AI를 초기화하지 않습니다. `baseline_passed`는 최소 조건 확인이며 키의 실제 랜덤성·서버 전체 보안 안전성을 증명하지 않습니다. SSH·IAM·IMDSv2와 운영 설정은 별도 확인입니다. 운영 확인 결과는 아직 미수신입니다.

### 사용자 기준 로그 조회

`GET /api/v1/logs?limit=10&offset=0&session_id=1` 응답 예시:

```json
{"total":2,"items":[{"id":2,"user_id":1,"username":"demo_user","session_id":1,"role":"assistant","content":"감리는 ...","latency_ms":1200,"status":"success","error_message":null,"created_at":"2026-10-04T00:00:01"}]}
```

필드 설명용 축약 예시입니다. `total`은 필터의 전체 메시지 수이며 질문·답변은 각각 한 행입니다. 일반 사용자는 자신의 로그만 보고, 관리자(`is_admin`)만 다른 사용자 `user_id`로 필터링할 수 있습니다. 가입 시 관리자가 되지 않으며 별도 관리자 UI는 없습니다. `limit` 1~200, `offset` 0 이상, `status` 필터를 지원합니다. 현재 AI 타임아웃도 DB status는 `error`이며 세부 사유는 `error_message`입니다.

## DB 구조와 검증 방법

```text
users (1) ── (N) chat_sessions (1) ── (N) chat_messages
  └────────────────────────────── (N) chat_messages
```

| 테이블 | 필드 |
|---|---|
| `users` | `id` PK, `username` unique, `nickname`, `password_hash`, `is_active`, `is_admin`, `created_at` |
| `chat_sessions` | `id` PK, `user_id` FK, `title`, `created_at`, `updated_at` |
| `chat_messages` | `id` PK, `session_id` FK, `user_id` FK, `role`, `content`, `latency_ms`, `status`, `error_message`, `created_at` |

메시지의 `role`은 `user` / `assistant` 구분입니다. 현재 develop에는 회원의 현장 직책 필드가 없습니다. 서버 시작 시 테이블이 생성되지만 `create_all()`은 기존 컬럼을 변경하지 않으므로 모델 변경 때 배포 DB 반영 방법도 확인합니다.

평가자는 로그인한 프론트의 `logs.html`, 로그 API, 레포 루트의 `uv run python scripts/check_logs.py`, 또는 `scripts/check_logs.sql` 중 편한 방법으로 확인할 수 있습니다.

콘솔과 `logs/server.log`에 `request_received`, `ai_call_start`, `ai_call_success` / `ai_call_failed`, `db_save_success` / `db_save_failed` 이벤트가 남습니다. 세션·질문·답변 저장 이벤트는 `request_id`와 `entity=session|user_message|assistant_message`로 구분합니다. 초기 저장은 커밋 후에만 성공 이벤트를 기록하고 실패 시 rollback·실패 이벤트·JSON 500 안내를 반환합니다. DB 실패 로그에는 SQL·파라미터 대신 예외 종류만 기록합니다. SDK 초기화 실패가 조용히 Mock로 전환되는 기존 경로는 별도 후속 보완점입니다.

## 배포와 협업

서버 실행·환경 변수·HTTPS·systemd는 [최소 배포 가이드](docs/deployment.md)를 따릅니다. Vercel에는 정적 프론트만, EC2에는 백엔드와 SQLite를 둡니다. RDS·Docker·로드 밸런서·자동 배포는 필수 조건이 아닙니다.

배포 브랜치는 선택할 수 있습니다. 팀의 안정 배포 기준은 main으로 두되 PR #8 병합 전 최신 기능은 develop에 있습니다. **승인과 병합은 다른 상태**입니다. main 배포 시 포함된 커밋을 확인하고 BE/FE 각각의 배포 브랜치를 기록합니다.

| 배포 확인 항목 | 현재 상태 |
|---|---|
| 프론트 Production URL / 백엔드 HTTPS URL | https://b7-1-chat-fe.vercel.app / https://b71chatbe.ddns.net. Codex HTTP 확인 |
| BE 배포 브랜치와 커밋 | 서버 로컬 `dev/log-ec2-deploy`, `4ce07e4971f32702c69e514807c1577c6517ad2c` — Aside 보고 |
| FE 배포 브랜치와 커밋 | `dev/log-frontend-integration`, `6fd410e458a2234a7d1d5c459f24f2f4bacfeac9` — Aside 배포 보고, Codex 공개 파일 내용 일치 확인 |
| 배포 브라우저 가입·로그인·Demo 질문·로그 조회 | 2026-10-04 사용자 직접 시험 성공, 새로고침 후 기록 재조회 확인 |
| 실제 AI 질문·문맥·DB 저장 확인일 | 2026-10-04 사용자 직접 키 입력·서버 재시작 후 실제 답변과 같은 대화의 후속 표 정리·로그 화면 확인. Codex의 Google 사용량 조회는 미실시 |

팀 합의는 개인 작업 브랜치 → `develop` 대상 PR → 리뷰 흐름입니다. 리뷰어는 감독 `dolphin1404`를 지정하며 `develop → main` 병합은 감독이 수행합니다. 이번 문서 보완은 `dev/log-mission-docs`에서 작업하고 main/develop을 직접 변경하지 않습니다.

### 팀 구성과 개인별 작업 요약

아래는 Git 이력과 사용자 설명으로 확인 가능한 내용입니다. 미확인 담당자를 실제 기여자로 만들어 쓰지 않습니다.

| 역할 / 확인된 작성자 | 작업 요약 | 상세 문서 |
|---|---|---|
| 감독·인프라 / `dolphin1404` (Git 작성자 Kyumin Lee) | PR 템플릿, develop → main 통합 PR #8. 배포 실행은 미확인 | [의사결정록](docs/decision_log.md) |
| 인증 / Git 작성자 `bwmin` | 닉네임 모델·스키마, 비밀번호 정책·변경 API, 검증 오류 처리·테스트. dev/auth에 미병합 추가 작업 있음 | [Auth](docs/roles/auth_guide.md) |
| DB·로그 / `feelosophysics` (Git 작성자 alzznd) | 로그 페이지네이션·통계·CLI·SQL·DB 테스트, 도메인 문서·프롬프트, 이번 README 보완 | [Log/DB](docs/roles/log_db_guide.md) |
| AI 최종 담당자 | 담당자 확인·개인별 요약 추가 필요. 기존 구현은 존재 | [Chat](docs/roles/chat_api_guide.md) |
| 프론트 / 별도 담당자 없음 (사용자 설명) | DB·로그 담당자의 요청으로 가입·API 주소 연동 및 현장노트 UI 개편. `dev/log-frontend-integration`의 `ea431c8`까지 커밋·푸시·배포 완료 | [프론트 저장소](https://github.com/cocoa7-1/chat-fe) |

팀원별 유의미한 커밋 10회 이상은 모든 팀원에 대해 아직 충족됐다고 확인할 수 없습니다. [미션 점검표](docs/mission-checklist.md)에 확인 범위와 남은 항목을 기록했습니다. 실제 작업·검증·문서화 이력을 남기며 빈 커밋으로 수를 채우지 않습니다.

## 테스트

```bash
uv run pytest tests/ -v
uv run python scripts/check_logs.py
```

테스트는 데이터를 생성하므로 운영 DB·실제 AI 키를 사용하지 않고 별도 테스트 환경에서 실행합니다. `scripts/test_api.py`는 배포 서버에 접속하는 검증이 아니라 TestClient로 앱을 확인하는 보조 스크립트입니다. Mock 테스트 통과와 실제 AI·외부 배포 검증은 구분합니다.
