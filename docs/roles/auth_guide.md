# 🛡️ Role 1: 인증 & 보안 (Auth & Security) 담당자 완벽 가이드

> **환영합니다!** 이 문서는 처음 백엔드를 접하는 팀원도 **회원가입, 로그인, 비밀번호 암호화(Bcrypt), JWT 토큰 발급 및 사용자 보호**를 쉽고 재미있게 실습하며 마스터할 수 있도록 작성된 단계별 가이드입니다.

---

## 🌟 1. 이 파트의 본질적 의미와 중요성 (Why this matters)

웹 서비스에서 '인증(Authentication)'은 **사용자가 누구인지 확인하고, 개인의 소중한 대화 기록과 권한을 안전하게 지키는 성벽**입니다.

1. **비밀번호를 절대 평문으로 저장하지 않는 이유 (Bcrypt)**
   - 데이터베이스가 해킹당하더라도 원래 비밀번호를 알 수 없도록 **단방향 해시 암호화(Bcrypt)**와 **Salt(소금 치기)**를 적용합니다.
2. **세션 쿠키 대신 JWT(JSON Web Token)를 쓰는 이유**
   - 서버가 수만 명의 로그인 상태를 메모리에 일일이 기억(Stateful)하지 않아도, 클라이언트가 서명된 JWT 토큰을 들고 오면 서버가 수학적으로 유효성을 즉시 검증(Stateless)할 수 있습니다. 프론트엔드(Vercel)와 백엔드(AWS EC2)가 분리된 현대적 아키텍처에 완벽합니다.
3. **의존성 주입(`Depends(get_current_user)`)의 마법**
   - 모든 API마다 일일이 "로그인했나?" 검사하는 코드를 복붙하지 않고, FastAPI의 `Depends`를 통해 단 한 줄로 인증된 사용자 객체(`User`)를 주입받아 비인가 접근을 원천 차단합니다.

---

## 📂 2. 내가 맡은 핵심 파일 및 디렉토리 구조

| 파일 경로 | 핵심 역할 | 내가 주로 만질 부분 |
| :--- | :--- | :--- |
| `app/api/v1/auth.py` | 회원가입/로그인/내정보 라우터 | 엔드포인트 URL, 응답 메시지, 비즈니스 로직 |
| `app/core/security.py` | Bcrypt 비밀번호 해싱 & JWT 생성/검증 | 토큰 만료 시간, 암호화 알고리즘 |
| `app/api/deps.py` | 현재 로그인된 사용자 검증 의존성 | Bearer 헤더 파싱, 401 예외 처리 |
| `app/models/user.py` | SQLite `users` 테이블 SQLAlchemy 모델 | 유저 컬럼 정의 (id, username, password 등) |
| `app/schemas/auth.py` | Pydantic 요청/응답 검증 DTO | 아이디/비밀번호 길이 검증, 에러 문구 |
| `tests/test_auth.py` | 인증 자동화 단위 테스트 | 회원가입 성공/실패, 토큰 검증 테스트 케이스 |

---

## 🚀 3. 당장 5분 만에 시작하는 체크리스트

```bash
# 1. 내 브랜치로 이동
git checkout dev/auth

# 2. 내 파트 테스트 실행해보기 (모두 통과하는지 확인!)
pytest tests/test_auth.py -v

# 3. 백엔드 서버 띄우기
uvicorn app.main:app --port 8000 --reload
```
- 브라우저에서 `http://localhost:8000/docs`에 접속하여 `auth` 태그의 API 목록(`register`, `login`, `me`)을 직접 눌러서 테스트해보세요!

---

## 🛠️ 4. 단계별 손쉬운 실습 과제 4단계 (Hands-on Experiments)

아래 과제를 하나씩 진행하면서 코드를 수정하고 테스트해보세요. 자연스럽게 실력이 늘어납니다!

### 🟢 Level 1: 비밀번호 최소 길이 유효성 검사 추가하기
- **파일**: `app/schemas/auth.py`
- **목표**: 비밀번호가 6자(또는 8자) 미만일 때 예쁜 한국어 에러 메시지를 반환하도록 `@field_validator` 추가
- **힌트**:
  ```python
  from pydantic import field_validator

  class UserCreate(BaseModel):
      username: str
      password: str

      @field_validator("password")
      def validate_password_len(cls, v):
          if len(v) < 6:
              raise ValueError("비밀번호는 최소 6자 이상이어야 합니다.")
          return v
  ```

### 🟡 Level 2: `User` 모델에 닉네임(`nickname`) 필드 추가해보기
- **파일**: `app/models/user.py`, `app/schemas/auth.py`, `app/api/v1/auth.py`
- **목표**: 사용자가 가입할 때 닉네임을 함께 입력받고, `GET /api/v1/auth/me`에서 닉네임도 함께 반환하도록 확장

### 🟠 Level 3: 비밀번호 변경 엔드포인트(`PUT /api/v1/auth/password`) 만들어보기
- **파일**: `app/api/v1/auth.py`, `app/schemas/auth.py`
- **목표**: 현재 비밀번호(`current_password`)와 새 비밀번호(`new_password`)를 받아 검증 후 비밀번호를 갱신하는 기능 구현

### 🔴 Level 4: 새 기능에 대한 Pytest 테스트 코드 추가하기
- **파일**: `tests/test_auth.py`
- **목표**: 비밀번호가 짧을 때 422 에러가 발생하는지 검증하는 `test_short_password_validation()` 함수 작성

---

## 📝 5. 10회 이상 의미 있는 커밋(Commit) 분할 레시피

미션 요구사항(팀원별 10회 이상 커밋)을 쉽게 달성할 수 있는 추천 커밋 흐름입니다:

1. `feat(auth): Add username length validation in UserCreate schema`
2. `feat(auth): Add password complexity validator in Pydantic schema`
3. `test(auth): Add unit test for invalid password length`
4. `feat(auth): Add nickname field to User model and UserResponse schema`
5. `refactor(auth): Improve error response messages for duplicate registration`
6. `feat(auth): Implement change password endpoint (PUT /api/v1/auth/password)`
7. `test(auth): Add unit test for password change flow`
8. `docs(auth): Update Auth API documentation and Swagger descriptions`
9. `refactor(security): Add token expiration configuration check`
10. `test(auth): Ensure 100% test coverage for auth endpoints`

---

## ❓ 6. 자주 겪는 오류 및 해결책 (Troubleshooting)

- **`401 Unauthorized - 로그인이 필요한 서비스입니다`**:
  - Swagger UI 상단의 **`Authorize`** 버튼을 누르고 `Bearer <발급받은_토큰>`을 입력했는지 확인하세요.
- **`422 Unprocessable Entity`**:
  - 요청 Body의 JSON 필드명(`username`, `password`)이 스키마와 정확히 일치하는지 확인하세요.
