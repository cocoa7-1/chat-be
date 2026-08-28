# 🏗️ 건설 안전 & 시공 전문 AI 튜터 - 백엔드 API (`chat-be`)

FastAPI 기반의 실시간 스트리밍 건설 안전 & 시공 전문 AI 챗봇 백엔드 서비스입니다. Google AI Studio Gemma 4 26B API 연동, Server-Sent Events (SSE) 실시간 토큰 스트리밍, SQLite DB 대화 로그 영속화, JWT 기반 사용자 인증, 구조화된 4대 로깅 시스템 및 Vercel/AWS EC2 배포 파이프라인을 지원합니다.

---

## 👥 4인 팀 역할 분담 및 브랜치 가이드

본 레포지토리는 4인 팀 협업과 미션 요구사항 충족을 위해 명확하게 역할과 브랜치가 분리되어 있습니다:

| 역할 (Role) | 브랜치 | 주요 담당 모듈 | 상세 가이드 문서 |
| :--- | :--- | :--- | :--- |
| 👑 **감독 & 인프라 (Director)** | `main` / `develop` | 아키텍처 검토, PR 리뷰, 브랜치 관리, AWS EC2 배포 | [📖 ADR 의사결정록](docs/decision_log.md) |
| 🛡️ **Role 1: 인증 & 보안 (Auth)** | `dev/auth` | `app/api/v1/auth.py`, `app/core/security.py`, `app/models/user.py` | [📖 Auth 가이드](docs/roles/auth_guide.md) |
| 💾 **Role 2: 데이터 & 로깅 (Log/DB)** <br>*(내 담당)* | `dev/log` | `app/api/v1/logs.py`, `app/core/database.py`, `app/models/chat.py` | [📖 Log/DB 가이드](docs/roles/log_db_guide.md) |
| 🤖 **Role 3: AI 파이프라인 (Chat)** | `dev/chat` | `app/api/v1/chat.py`, `app/services/gemini_service.py` | [📖 Chat 가이드](docs/roles/chat_api_guide.md) |

---

## 📁 디렉토리 구조
```text
chat-be/
├── app/
│   ├── api/
│   │   ├── deps.py              # 인증 의존성 주입 (get_current_user)
│   │   └── v1/
│   │       ├── auth.py          # [Role 1] 회원가입, 로그인, JWT 발급
│   │       ├── chat.py          # [Role 3] SSE 실시간 스트리밍, 세션 CRUD
│   │       └── logs.py          # [Role 2] 대화 로그 조회 및 통계
│   ├── core/
│   │   ├── config.py            # Pydantic 기반 환경변수 설정
│   │   ├── database.py          # SQLAlchemy SQLite 엔진 & 세션 관리
│   │   ├── logging.py           # 구조화된 로깅 시스템
│   │   ├── middlewares.py       # Request ID 발급 및 상관관계 추적 미들웨어
│   │   └── security.py          # Bcrypt 비밀번호 해싱 & JWT 생성/검증
│   ├── models/
│   │   ├── user.py              # User DB 모델
│   │   └── chat.py              # ChatSession, ChatMessage DB 모델
│   ├── schemas/
│   │   ├── auth.py              # 인증 Pydantic DTO
│   │   └── chat.py              # 채팅/세션 Pydantic DTO
│   ├── services/
│   │   └── gemini_service.py    # Google Gemini API 연동 & 컨텍스트 주입 & Mock 모드
│   └── main.py                  # FastAPI 앱 진입점 및 CORS 설정
├── docs/
│   ├── roles/                   # 팀원별 파트 상세 가이드 문서
│   │   ├── auth_guide.md
│   │   ├── log_db_guide.md
│   │   └── chat_api_guide.md
│   ├── decision_log.md          # 아키텍처 의사결정 기록 (ADR)
│   └── deep_dive_study_guide.md # 심층 엔지니어링 학습 가이드
├── scripts/
│   ├── check_logs.py            # 터미널용 DB 로그 검증 CLI 스크립트
│   ├── check_logs.sql           # SQLite 직접 쿼리용 SQL 파일
│   ├── test_api.py              # 자동 API 엔드포인트 검증 스크립트
│   └── run_public.py            # 외부 평가용 원클릭 터널링 스크립트
├── tests/                       # Pytest 단위/통합 테스트 스위트
│   ├── test_auth.py
│   ├── test_chat.py
│   └── test_db.py
├── requirements.txt             # Python 패키지 의존성 목록
├── .env.example                 # 환경변수 템플릿
├── pytest.ini                   # Pytest 설정
└── README.md
```

---

## ⚡ 빠른 시작 (Getting Started)

### 1. 가상환경 생성 및 패키지 설치
```bash
# 가상환경 생성
python -m venv .venv

# 가상환경 활성화 (Windows PowerShell)
.venv\Scripts\Activate.ps1

# 가상환경 활성화 (Mac/Linux)
# source .venv/bin/activate

# 의존성 패키지 설치
pip install -r requirements.txt
```

### 2. 환경변수 설정
`.env.example` 파일을 복사하여 `.env` 파일을 생성합니다:
```bash
cp .env.example .env
```

`.env` 파일 내용:
```ini
APP_ENV=development
APP_NAME=AI Learning Tutor Backend
DEBUG=true
HOST=0.0.0.0
PORT=8000

# SQLite 데이터베이스
DATABASE_URL=sqlite:///./chatbot.db

# JWT 보안 설정
JWT_SECRET_KEY=dev_secret_key_change_in_production_1234567890
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# Google Gemini API 설정 (미입력 시 스마트 Demo Mock 모드로 동작)
GEMINI_API_KEY=
GEMINI_MODEL_NAME=gemini-2.5-flash
AI_TIMEOUT_SECONDS=10
```

### 3. 서버 실행
```bash
uvicorn app.main:app --reload --port 8000
```
- Swagger UI (API 문서): `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

---

## 🧪 테스트 및 품질 검증

```bash
# 전체 단위 테스트 실행
pytest

# 로그 적재 확인 스크립트
python scripts/check_logs.py

# API 동작 일괄 테스트
python scripts/test_api.py
```

---

## 🤝 Git 브랜치 협업 가이드

1. **`main`**: 안정적인 배포 브랜치
2. **`develop`**: 개발 통합 브랜치
3. **`feature/<role>-<feature_name>`**: 개별 작업 브랜치
   - 예: `feature/auth-password-reset`
   - 예: `feature/db-pagination`
   - 예: `feature/chat-system-prompt`
4. 작업 완료 후 `develop` 브랜치로 Pull Request(PR) 생성 -> 코드 리뷰 후 머지
