# 🤖 Role 3: AI 파이프라인 & 채팅 API (Chat & AI) 담당자 완벽 가이드

> **환영합니다!** 본 문서는 **Google GenAI (Gemma 4 26B / Gemini) 연동, Server-Sent Events (SSE) 실시간 토큰 스트리밍, 대화 문맥(Context) 주입 및 타임아웃/장애 대응**을 완벽하게 마스터하기 위한 실전 가이드입니다.

---

## 🌟 1. 이 파트의 본질적 의미와 중요성 (Why this matters)

AI 챗봇 서비스의 **가장 핵심적인 심장이자 사용자가 직접 대화하며 감탄하는 두뇌** 영역입니다.

1. **REST JSON 대신 SSE(Server-Sent Events) 스트리밍을 쓰는 이유**
   - AI가 긴 답변을 다 생성할 때까지 몇 초 동안 사용자를 멍하니 기다리게(블로킹) 하지 않고, 생성되는 토큰(글자)을 실시간으로 화면에 타자 치듯(Streaming) 전송하여 체감 속도를 극대화합니다.
2. **대화 문맥(Context Window) 주입의 원리**
   - AI 모델 자체는 이전 대화를 기억하지 못합니다(Stateless). 따라서 우리가 DB에서 **최근 N개의 대화 기록(`recent_history`)을 조회하여 현재 질문과 함께 묶어서 프롬프트로 전달**해야 비로소 "아까 말한 그거 다시 설명해줘" 같은 연속성 있는 대화가 가능해집니다.
3. **타임아웃 및 장애 방어(`AI_TIMEOUT`)의 필요성**
   - 외부 AI 서버가 네트워크 지연이나 과부하로 멈췄을 때 우리 백엔드 서버까지 멈추지 않도록, `asyncio.wait_for(..., timeout=30)`로 안전하게 차단하고 사용자에게 친절한 안내 메시지를 전달해야 합니다.

---

## 📂 2. 내가 맡은 핵심 파일 및 디렉토리 구조

| 파일 경로 | 핵심 역할 | 내가 주로 만질 부분 |
| :--- | :--- | :--- |
| `app/api/v1/chat.py` | SSE 스트리밍 라우터 & 세션 관리 | 스트리밍 엔드포인트 (`/stream`), 세션 CRUD |
| `app/services/gemini_service.py` | AI SDK 연동, 문맥 조립, Mock 폴백, 지연시간 측정 | 프롬프트 조립, 스트리밍 파싱, 에러 처리 |
| `app/schemas/chat.py` | 채팅 Pydantic 입출력 DTO | 메시지 최대 길이 검증 (2000자 제한) |
| `tests/test_chat.py` | 세션 생성/조회, Mock 스트리밍, 타임아웃 단위 테스트 | AI 파이프라인 검증 테스트 케이스 |

---

## 🚀 3. 당장 5분 만에 시작하는 체크리스트

```bash
# 1. 내 브랜치로 이동
git checkout dev/chat

# 2. 내 파트 테스트 실행해보기
pytest tests/test_chat.py -v

# 3. CLI API 자동 검증 스크립트 실행해보기
python scripts/test_api.py
```

---

## 🛠️ 4. 단계별 손쉬운 실습 과제 4단계 (Hands-on Experiments)

### 🟢 Level 1: 시스템 프롬프트(튜터 페르소나) 수정해보기
- **파일**: `.env` 및 `app/core/config.py`
- **목표**: `SYSTEM_INSTRUCTION` 문구를 수정하여 챗봇의 말투(예: 건설 안전 명장 컨셉)를 바꾸고 답변 톤 변화 관찰하기

### 🟡 Level 2: 빈 메시지 또는 공백만 입력 시 차단하는 유효성 검사 추가
- **파일**: `app/schemas/chat.py`
- **목표**: 사용자가 스페이스바만 누르고 전송했을 때 422 에러와 함께 "메시지 내용을 입력해주세요"를 반환하도록 validator 추가

### 🟠 Level 3: 대화 문맥 기억 개수(`MAX_HISTORY_MESSAGES`)를 5개 $\rightarrow$ 15개로 변경하고 테스트
- **파일**: `.env`, `app/services/gemini_service.py`
- **목표**: 이전 대화가 얼마나 길게 AI 프롬프트에 주입되는지 로그와 응답 결과를 통해 확인

### 🔴 Level 4: 인위적으로 1초 타임아웃을 걸어 에러 응답 배너 확인하기
- **파일**: `.env` (`AI_TIMEOUT_SECONDS=1`)
- **목표**: 타임아웃 발생 시 화면에 `⚠️ 현재 응답이 지연되고 있어요. (error: AI_TIMEOUT)`가 예쁘게 출력되는지 검증

---

## 📝 5. 10회 이상 의미 있는 커밋(Commit) 분할 레시피

1. `feat(chat): Add empty message and whitespace validation in ChatMessageCreate schema`
2. `feat(ai): Update construction domain tutor system prompt instructions`
3. `test(chat): Add test case for empty message rejection`
4. `feat(ai): Improve mock response generator with structural markdown tables`
5. `refactor(chat): Optimize multi-turn history slicing logic in gemini_service`
6. `feat(chat): Add timeout exception handler and graceful fallback response`
7. `test(chat): Add unit test for AI timeout defense mechanism`
8. `feat(chat): Implement delete chat session endpoint (DELETE /sessions/{id})`
9. `docs(chat): Document SSE streaming event protocol and client consumption guide`
10. `test(chat): Ensure end-to-end coverage for chat streaming and DB persist pipeline`

---

## ❓ 6. 자주 겪는 오류 및 해결책 (Troubleshooting)

- **`404 NOT_FOUND - AI 모델을 찾을 수 없습니다`**:
  - `.env` 파일의 `GEMINI_MODEL_NAME`이 `gemma-4-26b-a4b-it` 또는 `gemini-2.5-flash`로 정확히 지정되어 있는지 확인하세요.
- **API 키가 없을 때**:
  - `GEMINI_API_KEY=""` 상태에서도 스마트 Mock 모드가 자동으로 동작하므로 키 없이도 100% 실습 및 개발이 가능합니다!
