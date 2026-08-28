# 🤖 Role 3: AI 파이프라인 & 채팅 API (Chat & AI) 담당자 가이드

본 문서는 **Google Gemini API 연동, SSE(Server-Sent Events) 실시간 토큰 스트리밍, 대화 문맥(Context) 주입 및 타임아웃/장애 대응**을 담당하는 팀원을 위한 개발 및 분석 가이드입니다.

---

## 📌 1. 담당 영역 및 핵심 파일

| 구분 | 파일 경로 | 설명 |
| :--- | :--- | :--- |
| **API 라우터** | `app/api/v1/chat.py` | SSE 스트리밍 엔드포인트 (`/stream`), 대화방(세션) CRUD API |
| **AI 서비스** | `app/services/gemini_service.py` | Google GenAI SDK 래퍼, 프롬프트 컨텍스트 조립, Mock 폴백, 지연시간 측정 |
| **데이터 스키마** | `app/schemas/chat.py` | Pydantic 입출력 검증 (`ChatRequest`, `SessionResponse`, `MessageResponse`) |
| **단위 테스트** | `tests/test_chat.py` | 세션 생성/조회, Mock 스트리밍 응답, 타임아웃 방어 테스트 |

---

## ⚡ 2. 실시간 스트리밍 & 대화 문맥 흐름

```
[클라이언트 (chat-fe)]
       │
       ▼ 1. POST /api/v1/chat/stream { message: "FastAPI 질문", session_id: 1 }
 [chat.py: stream_chat]
       │
       ├─ 2. 최근 N개(5~10개) 대화 이력 조회 (DB `chat_messages`)
       │
       ├─ 3. [gemini_service.py: generate_chat_stream] 호출
       │       - 시스템 프롬프트(튜터 페르소나) + 이전 대화 기록 + 현재 질문 결합
       │       - Gemini 2.5 Flash / Gemma 4 모델로 스트리밍 요청
       │
       ├─ 4. 토큰 생성될 때마다 SSE 이벤트 yield
       │       - event: message, data: {"text": "토큰..."}
       │
       ├─ 5. 완료 시 총 소요 시간(ms) 계산
       │       - event: done, data: {"latency_ms": 420, "status": "success"}
       │
       └─ 6. 백그라운드 DB 저장 (사용자 질문 + AI 응답 + Latency)
```

---

## 🛡️ 3. 장애 대응 및 타임아웃 방어 로직

AI API가 응답하지 않거나 타임아웃이 발생할 때 서버가 중단되지 않고 사용자에게 명확한 에러를 전달합니다:

```python
try:
    async with asyncio.timeout(settings.AI_TIMEOUT_SECONDS):
        async for chunk in stream_generator:
            yield format_sse("message", {"text": chunk.text})
except TimeoutError:
    logger.error("AI_TIMEOUT occurred.")
    yield format_sse("error", {
        "error": "AI_TIMEOUT",
        "message": "현재 응답이 지연되고 있어요. 잠시 후 다시 시도해 주세요. (error: AI_TIMEOUT)"
    })
```

### 💡 스마트 Demo Mock 폴백 모드
`.env` 파일에 `GEMINI_API_KEY`가 입력되어 있지 않아도, `gemini_service.py`가 자동으로 데모 모드로 전환되어 실제 스트리밍과 동일한 모의 응답을 반환하므로 로컬 환경에서 끊김 없이 개발을 진행할 수 있습니다.

---

## 🧪 4. 테스트 및 검증 방법

### 1) 자동화 테스트 실행
```bash
pytest tests/test_chat.py -v
```

### 2) CLI API 테스트 스크립트 실행
```bash
python scripts/test_api.py
```

### 3) cURL / HTTPie로 스트리밍 엔드포인트 수동 호출
```bash
curl -N -X POST http://localhost:8000/api/v1/chat/stream \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <YOUR_ACCESS_TOKEN>" \
  -d '{"message": "안녕! 너는 누구야?"}'
```
