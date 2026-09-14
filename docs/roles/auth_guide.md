# 🛡️ Role 1: 인증 & 보안 (Auth & Security) 동료와 함께하는 10단계 페어 실습 가이드

> **환영합니다!** 이 문서는 프로그래밍과 AI/SW 개발을 막 시작한 동료와 함께, **건설 안전 AI 튜터 서비스의 회원가입, 로그인, Bcrypt 비밀번호 암호화, JWT 토큰 및 사용자 접근 제어**를 가장 쉽고 재미있게 마스터하기 위한 실전 페어 프로그래밍 가이드입니다.
> 
> **진행 원칙**: 나란히 앉아(또는 화면 공유로) **[1개 작업 선정 → 동료가 직접 타이핑 → pytest 녹색불 확인 → 1커밋 → 동료의 한 줄 설명]** 핑퐁 사이클로 진행합니다.

---

## 🌟 1. 세 가지 핵심 개념을 잡는 '일상 물리 비유' (Mental Anchors)

백엔드 인증의 3대 수학적/추상적 개념을 일상생활의 사물로 먼저 머릿속에 담고 시작합니다.

### 🍅 ① Bcrypt 비밀번호 암호화 = "되돌릴 수 없는 믹서기 주스"
- **왜 쓰는가?**: DB가 해킹당하더라도 해커가 사용자의 원래 비밀번호를 알아낼 수 없게 만들기 위해서입니다.
- **비유**: 토마토와 사과를 넣고 믹서기를 돌려 주스를 만들면, 주스를 보고 원래 토마토의 모양을 복원할 수 없습니다(**단방향성**).
- **그럼 로그인은 어떻게 검사하나?**: 사용자가 로그인할 때 입력한 비밀번호를 같은 믹서기(같은 Salt/해시 알고리즘)에 돌려 나온 주스의 색깔/맛(해시 문자열)이 DB에 저장된 주스와 일치하는지만 대조합니다.

### 🎟️ ② JWT (JSON Web Token) = "위조 방지 도장이 찍힌 놀이공원 손목띠"
- **왜 쓰는가?**: 서버가 수만 명의 로그인 상태를 일일이 장부에 적어두지 않아도(**Stateless, 무상태**), 사용자가 증명서를 들고 다니게 하기 위함입니다.
- **비유**: 놀이공원에서 표를 사면 손목에 특수 형광 도장이 찍힌 띠(JWT)를 채워줍니다. 롤러코스터 입구에서는 직원이 본사 장부를 뒤적이지 않고, 손목띠의 도장(디지털 서명)이 진짜인지만 확인하고 즉시 통과시킵니다.
- **JWT 3단 해부**:
  - **헤더(Header)**: 손목띠 재질 (어떤 암호화 알고리즘인가?)
  - **페이로드(Payload)**: 손목띠에 적힌 내용 (사용자 ID, 이름, 만료시간 등)
  - **서명(Signature)**: 관리자만 가진 도장 (서버의 비밀키로 날인하여 1글자만 위조해도 즉시 탄로남)

### 👮 ③ FastAPI `Depends(get_current_user)` = "놀이기구 탑승구 표 검사원"
- **왜 쓰는가?**: 챗봇 API, 로그 조회 API 등 로그인한 사람만 들어와야 하는 수십 개의 방마다 매번 "너 표 있니?" 코드를 복붙하지 않기 위해서입니다.
- **비유**: 놀이기구 탑승구마다 숙련된 검사원(`Depends`)을 세워둡니다. 검사원이 손목띠를 검사해 가짜이거나 유효기간이 지났으면 401 에러로 쫓아내고, 정상이면 통과시켜 탑승자(`User` 객체)를 조종석(라우터 함수)으로 안내합니다.

---

## 🧭 2. 5분 만에 눈으로 확인하는 시각적 도구 2종 (Visual Check)

코드를 고치기 전에, 현재 작동하는 시스템의 입출력을 눈으로 직접 확인합니다.

```bash
# 1. 내 브랜치로 이동
git checkout dev/auth

# 2. 백엔드 서버 구동
uv run uvicorn app.main:app --port 8000 --reload
```

### 🔍 도구 1: Swagger UI 인터랙션 (`http://localhost:8000/docs`)
1. 브라우저에서 `http://localhost:8000/docs` 접속.
2. `POST /api/v1/auth/register`를 클릭하고 [Try it out] 클릭.
3. 원하는 `username`과 `password`를 넣고 [Execute] → `201 Created`와 생성된 사용자 정보 확인!
4. `POST /api/v1/auth/login`을 클릭하고 로그인 [Execute] → 반환된 `access_token` 복사!

### 🔍 도구 2: jwt.io 토큰 해부
1. [jwt.io](https://jwt.io) 사이트 접속.
2. 복사한 긴 외계어 토큰(`eyJhbGciOi...`)을 왼쪽 인풋창에 붙여넣기.
3. 오른쪽 창에 빨간색(헤더), 보라색(페이로드: 내 아이디, 만료시간)이 평문으로 디코딩되는 것을 동료와 함께 눈으로 확인!

---

## 🛠️ 3. 건설 안전 도메인 밀착형 10단계 페어 실습 레시피 (10-Commit Recipe)

> **팀 도메인**: 🏗️ **"건설 안전 & 시공 전문 AI 튜터"**  
> **미션 목표**: 회원(`User`) 가입 시 건설 현장 직책(`role`: 안전관리자, 현장작업자, 시공기술자)을 부여하고, 안전 관리 체계를 구축합니다.  
> **진행 방식**: 1단계마다 동료가 코드를 작성하고, 테스트 통과 후 커밋을 분할합니다.

---

### 🟢 Step 1: 비밀번호 최소 6자 검증 및 한글 안내 메시지
- **파일**: `app/schemas/auth.py`
- **작업**: `UserCreate`의 `validate_password`에서 길이가 6자 미만일 때 "비밀번호는 최소 6자 이상이어야 합니다." 에러를 던지도록 수정.
- **검증**: `uv run pytest tests/test_auth.py`
- **커밋 1**: `feat(auth): Enforce minimum 6-character password in UserCreate schema`
- **동료 한 줄 설명**: "비밀번호가 6글자보다 짧으면 Pydantic이 서버 앞단에서 바로 튕겨내도록 유효성 검사를 걸었어요."

---

### 🟢 Step 2: 비밀번호 길이 유효성 검사 단위 테스트 추가
- **파일**: `tests/test_auth.py`
- **작업**: `test_short_password_rejection()` 함수를 추가하여 3글자 비밀번호 전송 시 422 상태코드가 오는지 검증.
- **검증**: `uv run pytest tests/test_auth.py -k test_short_password`
- **커밋 2**: `test(auth): Add unit test for short password validation failure`
- **동료 한 줄 설명**: "짧은 비밀번호를 넣었을 때 정말로 422 에러가 나는지 테스트 코드로 자동 검증했어요."

---

### 🟢 Step 3: 아이디(username) 공백 및 특수문자 검증 로직 추가
- **파일**: `app/schemas/auth.py`
- **작업**: `validate_username`에서 앞뒤 공백 제거(`strip()`) 후 3자 미만 차단.
- **검증**: `uv run pytest tests/test_auth.py`
- **커밋 3**: `feat(auth): Add strict username whitespace and length validation`
- **동료 한 줄 설명**: "스페이스바만 누르고 가입하는 꼼수를 막기 위해 공백 검사를 강화했어요."

---

### 🟡 Step 4: 건설 현장 직책(role) 열거형(Enum) 및 모델 컬럼 추가
- **파일**: `app/models/user.py`
- **작업**: `User` 테이블에 `role` 컬럼 추가 (기본값: `"site_worker"` / 허용값: `safety_manager`, `site_worker`, `field_engineer`).
  ```python
  role: Mapped[str] = mapped_column(String(30), default="site_worker", nullable=False)
  ```
- **검증**: `uv run pytest tests/test_auth.py`
- **커밋 4**: `feat(user): Add construction site role column to User database model`
- **동료 한 줄 설명**: "우리 서비스가 건설 안전 튜터니까, DB 유저 테이블에 현장 작업자인지 안전관리자인지 구분하는 직책 칸을 만들었어요."

---

### 🟡 Step 5: 회원가입 요청 DTO(`UserCreate`)에 role 필드 추가
- **파일**: `app/schemas/auth.py`
- **작업**: `UserCreate`에 `role: Optional[str] = "site_worker"` 필드 추가 및 직책 유효성 검증(`safety_manager`, `site_worker`, `field_engineer` 중 하나인지).
- **검증**: `uv run pytest tests/test_auth.py`
- **커밋 5**: `feat(auth): Support construction role selection in UserCreate schema`
- **동료 한 줄 설명**: "가입할 때 자신이 안전관리자인지 현장작업자인지 선택해서 보낼 수 있도록 DTO를 확장했어요."

---

### 🟡 Step 6: 회원가입 라우터에서 role 필드 DB 저장 연동
- **파일**: `app/api/v1/auth.py`
- **작업**: `register` 엔드포인트에서 `User(..., role=user_in.role)`로 받아 DB에 저장하도록 연결.
- **검증**: `uv run pytest tests/test_auth.py`
- **커밋 6**: `feat(auth): Persist user construction role upon registration`
- **동료 한 줄 설명**: "가입 요청으로 들어온 직책 정보를 실제 데이터베이스에 영구 저장하도록 라우터를 연결했어요."

---

### 🟠 Step 7: 사용자 응답 DTO(`UserResponse`)에 role 필드 노출
- **파일**: `app/schemas/auth.py`
- **작업**: `UserResponse`에 `role: str` 필드를 추가하여, 회원가입 완료 및 내 정보 조회(`GET /me`) 시 직책이 화면에 표시되도록 설정.
- **검증**: `uv run pytest tests/test_auth.py`
- **커밋 7**: `feat(auth): Expose user construction role in UserResponse DTO`
- **동료 한 줄 설명**: "로그인하거나 내 정보를 조회할 때 프론트엔드가 내 직책을 알 수 있도록 응답 모델에 추가했어요."

---

### 🟠 Step 8: 직책별 회원가입 및 조회 E2E 테스트 케이스 작성
- **파일**: `tests/test_auth.py`
- **작업**: `test_register_with_construction_role()` 함수를 작성하여, `safety_manager`로 가입 후 `/me`를 불렀을 때 직책이 그대로 돌아오는지 검증.
- **검증**: `uv run pytest tests/test_auth.py`
- **커밋 8**: `test(auth): Verify registration and profile inquiry with construction role`
- **동료 한 줄 설명**: "안전관리자로 가입했을 때 프로필에 직책이 정확히 나오는지 전체 시나리오를 테스트했어요."

---

### 🔴 Step 9: Swagger 문서(docstring & tags) 한글 친절화
- **파일**: `app/api/v1/auth.py`
- **작업**: `/register`, `/login`, `/me` 각 함수의 docstring을 건설 안전 도메인 시나리오에 맞게 명확하고 친절한 한글 설명으로 보강.
- **검증**: 브라우저 `/docs` 새로고침하여 문서 설명 확인.
- **커밋 9**: `docs(auth): Enhance Swagger API descriptions for construction domain`
- **동료 한 줄 설명**: "평가자나 프론트엔드 팀원이 Swagger만 봐도 API를 쉽게 쓸 수 있도록 한글 안내를 상세하게 적었어요."

---

### 🔴 Step 10: 전체 통합 회귀 테스트 검증 및 코드 정리
- **파일**: `tests/test_auth.py`
- **작업**: 불필요한 디버깅 출력 정리, 전체 인증 테스트 케이스가 100% Pass하는지 확인.
- **검증**: `uv run pytest tests/test_auth.py -v` (모든 테스트 PASSED)
- **커밋 10**: `test(auth): Ensure 100% test pass rate for construction auth pipeline`
- **동료 한 줄 설명**: "우리가 만든 10단계 인증 기능이 기존 시스템과 충돌 없이 완벽하게 동작함을 최종 검증했어요."

---

## 🎤 4. 구술 평가 완벽 대비 3대 질문 족보 (Feynman Checkpoint)

평가자나 면접관이 "인증 파트 어떻게 만드셨어요?"라고 물어볼 때 당당하게 대답할 수 있는 3대 핵심 문답입니다. 나란히 앉아 서로 질문하고 대답해보세요!

### ❓ Q1. "비밀번호는 왜 DB에 그대로 저장하지 않고 Bcrypt로 해싱했나요?"
> **🗣️ 답변 스크립트**:  
> "DB가 물리적으로 유출되거나 해킹당하더라도 사용자의 비밀번호를 절대 역추적할 수 없도록 **단방향 암호화(Bcrypt)**를 적용했습니다.  
> 또한 같은 비밀번호라도 서로 다른 암호문이 나오도록 **Salt(소금)**를 뿌려서, 레인보우 테이블 같은 무차별 대입 공격을 원천 차단했습니다."

### ❓ Q2. "세션 방식 대신 왜 JWT 토큰을 선택하셨나요?"
> **🗣️ 답변 스크립트**:  
> "저희 서비스는 프론트엔드(Vercel)와 백엔드(AWS EC2)가 물리적으로 분리되어 있습니다.  
> 세션 방식을 쓰면 백엔드 서버가 모든 유저의 로그인 상태를 메모리나 DB에 보관해야 해서 서버에 부담이 큽니다.  
> 반면 **JWT는 사용자 정보와 만료시간을 토큰 자체에 담고 서버의 비밀키로 서명**하기 때문에, 서버가 상태를 저장하지 않는(Stateless) 구조로 가볍고 안전하게 확장할 수 있어 채택했습니다."

### ❓ Q3. "로그인하지 않은 사용자가 챗봇 API를 호출하면 어떻게 막나요?"
> **🗣️ 답변 스크립트**:  
> "FastAPI의 강력한 기능인 **`Depends(get_current_user)` 의존성 주입**을 사용했습니다.  
> 요청 헤더의 `Authorization: Bearer <토큰>` 또는 HTTP-Only 쿠키를 가로채서 서명을 검증합니다.  
> 토큰이 없거나 만료되었으면 라우터 본문 코드가 실행되기도 전에 **`401 Unauthorized` 에러를 즉시 반환**하여 서비스를 완벽하게 보호합니다."

---

## 🤝 5. PR(Pull Request) 올릴 때 팁

모든 10개 커밋을 완료한 후, `develop` 브랜치를 향해 PR을 올립니다.
- 브랜치: `dev/auth -> develop`
- PR 본문: `.github/pull_request_template.md`의 양식에 맞춰, 동료가 직접 느낀 점을 솔직하게 작성합니다:
  - **어떤 기능인가요?**: 건설 안전 도메인 직책 기반 회원가입 및 JWT 인증 파이프라인 구축
  - **내가 설명할 수 있는 부분**: Bcrypt 단방향 해싱 원리, JWT 구조, Depends를 통한 401 차단
  - **새로 알게 된 점**: Pydantic `@field_validator`로 프론트엔드 입력값을 서버에서 안전하게 걸러내는 방법!
