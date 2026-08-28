# 🛡️ Role 1: 인증 & 보안 (Auth & Security) 담당자 가이드

본 문서는 **회원가입, 로그인, JWT 토큰 발급, 비밀번호 해싱 및 접근 제어**를 담당하는 팀원을 위한 개발 및 분석 가이드입니다.

---

## 📌 1. 담당 영역 및 핵심 파일

| 구분 | 파일 경로 | 설명 |
| :--- | :--- | :--- |
| **API 라우터** | `app/api/v1/auth.py` | 회원가입, 로그인, 로그아웃, 내 정보 조회 엔드포인트 |
| **보안 유틸** | `app/core/security.py` | Bcrypt 비밀번호 해싱/검증, JWT 생성/디코딩 로직 |
| **의존성 주입** | `app/api/deps.py` | Bearer 토큰 및 쿠키로부터 현재 로그인된 사용자(`User`) 추출 |
| **데이터 모델** | `app/models/user.py` | SQLite `users` 테이블 SQLAlchemy 모델 |
| **데이터 스키마** | `app/schemas/auth.py` | Pydantic 요청/응답 검증 스키마 (`UserCreate`, `UserLogin`, `Token` 등) |
| **단위 테스트** | `tests/test_auth.py` | 회원가입, 로그인 실패/성공, 토큰 검증 테스트 |

---

## 🔄 2. 인증 파이프라인 흐름 (Authentication Flow)

```
[클라이언트 (chat-fe)]
       │
       ├─ 1. POST /api/v1/auth/register ──> [auth.py: register] ──> [security.py: get_password_hash] ──> [DB: users 저장]
       │
       ├─ 2. POST /api/v1/auth/login ─────> [auth.py: login] ────> [security.py: verify_password]
       │                                                                  │
       │                                                          (비밀번호 일치 시)
       │                                                                  ▼
       │                                                         [security.py: create_access_token]
       │                                                                  │
       │ <────── JWT 토큰 및 쿠키 반환 ───────────────────────────────────┘
       │
       └─ 3. GET /api/v1/chat/sessions (Authorization: Bearer <token>)
                 │
                 ▼
          [deps.py: get_current_user] ──> [security.py: decode_access_token] ──> [User 객체 주입]
```

---

## 💡 3. 핵심 코드 살펴보기

### 1) 비밀번호 단방향 암호화 (`app/core/security.py`)
```python
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)
```

### 2) JWT 토큰 발급 (`app/core/security.py`)
```python
from datetime import datetime, timedelta, timezone
from jose import jwt

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {"sub": subject, "exp": expire}
    return jwt.encode(to_encode, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
```

### 3) 보호된 엔드포인트 의존성 (`app/api/deps.py`)
다른 팀원들(Chat, Logs)의 API는 이 함수를 주입받아 비인가 요청을 차단합니다:
```python
def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = get_token_from_request(request)
    if not token:
        raise HTTPException(status_code=401, detail="로그인이 필요한 서비스입니다.")
    # 토큰 검증 및 유저 조회
    ...
```

---

## 🧪 4. 테스트 및 검증 방법

### 1) 자동화 테스트 실행
```bash
pytest tests/test_auth.py -v
```

### 2) Swagger UI를 통한 수동 테스트
1. 백엔드 실행: `uvicorn app.main:app --reload`
2. 브라우저에서 `http://localhost:8000/docs` 접속
3. `POST /api/v1/auth/register`로 새 계정 등록
4. `POST /api/v1/auth/login`으로 토큰 획득
5. 우측 상단 `Authorize` 버튼에 `Bearer <발급된_토큰>` 입력 후 `GET /api/v1/auth/me` 호출
